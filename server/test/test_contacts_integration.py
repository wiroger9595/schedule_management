"""
整合測試：聯絡人 CRUD + 刪除聯絡人 cascade

測試範圍：
1. 新增聯絡人（正常 / 自己email / 自己手機 / 重複email / 重複電話）
2. 新增聯絡人自動連結 contact_user_id（email 對應到 app 用戶）
3. 即時驗證 /validate（重複 / 自己）
4. 更新聯絡人（正常 / 重複欄位被擋）
5. 刪除聯絡人 cascade：
   a. 無活動 → 只刪聯絡人
   b. 聯絡人是 schedule.contact_id → 行程 + attend 一起刪
   c. 聯絡人是 attend.contact_id → attend + 對應行程一起刪
6. 隔離測試：刪 A 不影響 B 的資料
7. 刪除後聯絡人不在清單

前置：server 必須已在 localhost:7800 啟動，DB 可寫入
使用兩個測試帳號（每次執行自動確保存在）
"""

import pytest
import requests
import uuid
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:7800"

# ──────────────────────────────────────────────
# 測試帳號 (固定 email，每次 register 若已存在就跳過)
# ──────────────────────────────────────────────
USER_A_EMAIL = "test_contact_user_a@integration.test"
USER_A_PASS  = "TestPass123!"
USER_B_EMAIL = "test_contact_user_b@integration.test"
USER_B_PASS  = "TestPass123!"


# ──────────────────────────────────────────────
# 共用工具函式
# ──────────────────────────────────────────────

def _register_if_not_exists(email: str, password: str, full_name: str):
    res = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": email, "password": password, "full_name": full_name
    })
    # 400 = already registered — OK
    assert res.status_code in (200, 400), f"register failed: {res.text}"


def _login(email: str, password: str) -> str:
    """登入並回傳 Bearer token"""
    res = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"login failed: {res.text}"
    return res.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_contact(token: str, **kwargs) -> dict:
    res = requests.post(f"{BASE_URL}/api/contacts/", json=kwargs, headers=_headers(token))
    assert res.status_code == 200, f"create_contact failed: {res.text}"
    return res.json()


# Seed counter from current epoch so each test session gets unique schedule times
_schedule_counter = int(time.time())


def _next_schedule_times() -> tuple:
    """Generate a unique start/end time pair far in the future to avoid schedule conflicts."""
    global _schedule_counter
    _schedule_counter += 1
    # Spread across a 10-year window starting in 2100
    base = datetime(2100, 1, 1)
    start = base + timedelta(hours=_schedule_counter % (10 * 365 * 24))
    end = start + timedelta(minutes=30)
    return start.strftime("%Y-%m-%dT%H:%M:%S"), end.strftime("%Y-%m-%dT%H:%M:%S")


def _create_schedule(token: str, title: str, contact_id: int = None, attends: list = None) -> dict:
    """建立一筆手動行程，回傳 schedule dict（含 id = schedule_id）"""
    start, end = _next_schedule_times()
    payload = {
        "title": title,
        "start_time": start,
        "end_time":   end,
        "location": "測試地點",
        "latitude": 25.04,
        "longitude": 121.51,
    }
    if contact_id:
        payload["contact_id"] = contact_id
    if attends:
        payload["attends"] = attends
    res = requests.post(f"{BASE_URL}/api/schedules/", json=payload, headers=_headers(token))
    assert res.status_code == 200, f"create_schedule failed: {res.text}"
    return res.json()


def _get_contacts(token: str) -> list:
    res = requests.get(f"{BASE_URL}/api/contacts/", headers=_headers(token))
    assert res.status_code == 200
    return res.json()


def _get_schedules(token: str) -> list:
    res = requests.get(f"{BASE_URL}/api/schedules/", headers=_headers(token))
    assert res.status_code == 200
    return res.json()


def _delete_contact(token: str, contact_id: int) -> requests.Response:
    return requests.delete(f"{BASE_URL}/api/contacts/{contact_id}", headers=_headers(token))


def _unique_phone() -> str:
    return "09" + str(uuid.uuid4().int)[:8]


def _unique_email() -> str:
    return f"contact_{uuid.uuid4().hex[:8]}@example.test"


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def tokens():
    """建立測試用戶並回傳 {token_a, token_b}"""
    _register_if_not_exists(USER_A_EMAIL, USER_A_PASS, "Test User A")
    _register_if_not_exists(USER_B_EMAIL, USER_B_PASS, "Test User B")
    return {
        "a": _login(USER_A_EMAIL, USER_A_PASS),
        "b": _login(USER_B_EMAIL, USER_B_PASS),
    }


# ──────────────────────────────────────────────
# 1. 新增聯絡人
# ──────────────────────────────────────────────

class TestCreateContact:
    def test_create_basic(self, tokens):
        phone = _unique_phone()
        c = _create_contact(tokens["a"], nick_name="小明", phone=phone)
        assert c["id"]
        assert c["nick_name"] == "小明"
        assert c["phone"] == phone
        # cleanup
        _delete_contact(tokens["a"], c["id"])

    def test_create_requires_at_least_one_field(self, tokens):
        res = requests.post(f"{BASE_URL}/api/contacts/", json={}, headers=_headers(tokens["a"]))
        assert res.status_code == 400

    def test_cannot_add_self_by_email(self, tokens):
        res = requests.post(
            f"{BASE_URL}/api/contacts/",
            json={"nick_name": "自己", "email": USER_A_EMAIL},
            headers=_headers(tokens["a"])
        )
        assert res.status_code == 400
        assert "自己" in res.json()["detail"]

    def test_duplicate_phone_rejected(self, tokens):
        phone = _unique_phone()
        c = _create_contact(tokens["a"], nick_name="甲", phone=phone)
        res = requests.post(
            f"{BASE_URL}/api/contacts/",
            json={"nick_name": "乙", "phone": phone},
            headers=_headers(tokens["a"])
        )
        assert res.status_code == 400
        assert "電話" in res.json()["detail"]
        _delete_contact(tokens["a"], c["id"])

    def test_duplicate_email_rejected(self, tokens):
        email = _unique_email()
        c = _create_contact(tokens["a"], nick_name="甲", email=email)
        res = requests.post(
            f"{BASE_URL}/api/contacts/",
            json={"nick_name": "乙", "email": email},
            headers=_headers(tokens["a"])
        )
        assert res.status_code == 400
        assert "email" in res.json()["detail"]
        _delete_contact(tokens["a"], c["id"])

    def test_same_phone_allowed_for_different_users(self, tokens):
        """同一手機號不同用戶可以各自儲存"""
        phone = _unique_phone()
        ca = _create_contact(tokens["a"], nick_name="甲", phone=phone)
        cb = _create_contact(tokens["b"], nick_name="乙", phone=phone)
        assert ca["id"] != cb["id"]
        _delete_contact(tokens["a"], ca["id"])
        _delete_contact(tokens["b"], cb["id"])


# ──────────────────────────────────────────────
# 2. 自動連結 contact_user_id
# ──────────────────────────────────────────────

class TestAutoLinkContactUserId:
    def test_auto_link_when_email_matches_app_user(self, tokens):
        """新增聯絡人時 email 對應 User B → contact_user_id 自動填入"""
        c = _create_contact(tokens["a"], nick_name="B君", email=USER_B_EMAIL)
        assert c["contact_user_id"] is not None, "contact_user_id 應自動連結"
        _delete_contact(tokens["a"], c["id"])

    def test_no_auto_link_for_unknown_email(self, tokens):
        email = _unique_email()
        c = _create_contact(tokens["a"], nick_name="陌生人", email=email)
        assert c["contact_user_id"] is None
        _delete_contact(tokens["a"], c["id"])


# ──────────────────────────────────────────────
# 3. 即時驗證 /validate
# ──────────────────────────────────────────────

class TestValidateContact:
    def test_valid_new_info(self, tokens):
        res = requests.post(
            f"{BASE_URL}/api/contacts/validate",
            json={"email": _unique_email(), "phone": _unique_phone()},
            headers=_headers(tokens["a"])
        )
        assert res.status_code == 200
        assert res.json()["is_valid"] is True

    def test_self_email_invalid(self, tokens):
        res = requests.post(
            f"{BASE_URL}/api/contacts/validate",
            json={"email": USER_A_EMAIL},
            headers=_headers(tokens["a"])
        )
        data = res.json()
        assert data["is_valid"] is False
        assert data["duplicate_field"] == "self_email"

    def test_duplicate_email_invalid(self, tokens):
        email = _unique_email()
        c = _create_contact(tokens["a"], nick_name="甲", email=email)
        res = requests.post(
            f"{BASE_URL}/api/contacts/validate",
            json={"email": email},
            headers=_headers(tokens["a"])
        )
        data = res.json()
        assert data["is_valid"] is False
        assert data["duplicate_field"] == "email"
        _delete_contact(tokens["a"], c["id"])

    def test_exclude_contact_id_allows_self_update(self, tokens):
        """更新時排除自身 ID，相同 email 應視為有效"""
        email = _unique_email()
        c = _create_contact(tokens["a"], nick_name="甲", email=email)
        res = requests.post(
            f"{BASE_URL}/api/contacts/validate",
            json={"email": email, "exclude_contact_id": c["id"]},
            headers=_headers(tokens["a"])
        )
        assert res.json()["is_valid"] is True
        _delete_contact(tokens["a"], c["id"])


# ──────────────────────────────────────────────
# 4. 更新聯絡人
# ──────────────────────────────────────────────

class TestUpdateContact:
    def test_update_nick_name(self, tokens):
        c = _create_contact(tokens["a"], nick_name="舊名")
        res = requests.put(
            f"{BASE_URL}/api/contacts/{c['id']}",
            json={"nick_name": "新名"},
            headers=_headers(tokens["a"])
        )
        assert res.status_code == 200
        assert res.json()["nick_name"] == "新名"
        _delete_contact(tokens["a"], c["id"])

    def test_update_duplicate_email_rejected(self, tokens):
        email = _unique_email()
        c1 = _create_contact(tokens["a"], nick_name="甲", email=email)
        c2 = _create_contact(tokens["a"], nick_name="乙", phone=_unique_phone())
        res = requests.put(
            f"{BASE_URL}/api/contacts/{c2['id']}",
            json={"email": email},
            headers=_headers(tokens["a"])
        )
        assert res.status_code == 400
        _delete_contact(tokens["a"], c1["id"])
        _delete_contact(tokens["a"], c2["id"])

    def test_update_another_users_contact_rejected(self, tokens):
        c = _create_contact(tokens["a"], nick_name="甲")
        res = requests.put(
            f"{BASE_URL}/api/contacts/{c['id']}",
            json={"nick_name": "被改"},
            headers=_headers(tokens["b"])
        )
        assert res.status_code == 404
        _delete_contact(tokens["a"], c["id"])


# ──────────────────────────────────────────────
# 5. 刪除聯絡人 cascade
# ──────────────────────────────────────────────

class TestDeleteContactCascade:

    def test_delete_contact_no_schedule(self, tokens):
        """無關聯行程 → 只刪聯絡人"""
        c = _create_contact(tokens["a"], nick_name="孤獨聯絡人")
        contacts_before = len(_get_contacts(tokens["a"]))

        res = _delete_contact(tokens["a"], c["id"])
        assert res.status_code == 200, res.text

        contacts_after = _get_contacts(tokens["a"])
        ids_after = [x["id"] for x in contacts_after]
        assert c["id"] not in ids_after
        assert len(contacts_after) == contacts_before - 1

    def test_delete_contact_as_primary_on_schedule(self, tokens):
        """聯絡人是 schedule.contact_id → 行程也刪除"""
        c = _create_contact(tokens["a"], nick_name="主要聯絡人")
        s = _create_schedule(tokens["a"], title="主聯絡人測試行程", contact_id=c["id"])
        schedule_id = s.get("schedule_id") or s.get("id")

        schedules_before = _get_schedules(tokens["a"])
        sids_before = [x.get("schedule_id") or x.get("id") for x in schedules_before]
        assert schedule_id in sids_before, "行程應存在"

        res = _delete_contact(tokens["a"], c["id"])
        assert res.status_code == 200, res.text

        # 聯絡人已刪
        ids_after = [x["id"] for x in _get_contacts(tokens["a"])]
        assert c["id"] not in ids_after

        # 行程也刪了
        sids_after = [x.get("schedule_id") or x.get("id") for x in _get_schedules(tokens["a"])]
        assert schedule_id not in sids_after, "行程應被一起刪除"

    def test_delete_contact_as_attendee(self, tokens):
        """聯絡人是 attend.contact_id → attend 紀錄 + 行程一起刪"""
        c = _create_contact(tokens["a"], nick_name="出席者")
        s = _create_schedule(
            tokens["a"],
            title="出席者測試行程",
            attends=[{"contact_id": c["id"]}]
        )
        schedule_id = s.get("schedule_id") or s.get("id")

        sids_before = [x.get("schedule_id") or x.get("id") for x in _get_schedules(tokens["a"])]
        assert schedule_id in sids_before

        res = _delete_contact(tokens["a"], c["id"])
        assert res.status_code == 200, res.text

        ids_after = [x["id"] for x in _get_contacts(tokens["a"])]
        assert c["id"] not in ids_after

        sids_after = [x.get("schedule_id") or x.get("id") for x in _get_schedules(tokens["a"])]
        assert schedule_id not in sids_after, "出席者行程應被一起刪除"

    def test_delete_contact_cannot_delete_others_contact(self, tokens):
        """不能刪別人的聯絡人"""
        c = _create_contact(tokens["a"], nick_name="甲的聯絡人")
        res = _delete_contact(tokens["b"], c["id"])
        assert res.status_code == 404
        _delete_contact(tokens["a"], c["id"])


# ──────────────────────────────────────────────
# 6. 隔離測試：刪 A 不影響 B
# ──────────────────────────────────────────────

class TestIsolation:

    def test_deleting_contact_a_does_not_affect_contact_b(self, tokens):
        """刪聯絡人 A 不影響聯絡人 B 及其行程"""
        ca = _create_contact(tokens["a"], nick_name="聯絡人A")
        cb = _create_contact(tokens["a"], nick_name="聯絡人B")
        sb = _create_schedule(tokens["a"], title="B的行程", contact_id=cb["id"])
        sb_id = sb.get("schedule_id") or sb.get("id")

        # 刪 A
        res = _delete_contact(tokens["a"], ca["id"])
        assert res.status_code == 200

        # B 及其行程仍存在
        ids_after = [x["id"] for x in _get_contacts(tokens["a"])]
        assert cb["id"] in ids_after, "聯絡人B 不應被刪除"

        sids_after = [x.get("schedule_id") or x.get("id") for x in _get_schedules(tokens["a"])]
        assert sb_id in sids_after, "B的行程不應被刪除"

        # cleanup
        _delete_contact(tokens["a"], cb["id"])

    def test_user_a_schedule_not_deleted_by_user_b_contact_delete(self, tokens):
        """User B 刪自己的聯絡人，不影響 User A 的同名行程"""
        phone = _unique_phone()
        ca = _create_contact(tokens["a"], nick_name="同名甲", phone=phone)
        # B 也有一個同號聯絡人（不同用戶允許重複）
        cb = _create_contact(tokens["b"], nick_name="同名甲", phone=_unique_phone())

        sa = _create_schedule(tokens["a"], title="A的行程", contact_id=ca["id"])
        sa_id = sa.get("schedule_id") or sa.get("id")

        # B 刪自己的聯絡人
        _delete_contact(tokens["b"], cb["id"])

        # A 的聯絡人 + 行程仍在
        ids_after = [x["id"] for x in _get_contacts(tokens["a"])]
        assert ca["id"] in ids_after

        sids_after = [x.get("schedule_id") or x.get("id") for x in _get_schedules(tokens["a"])]
        assert sa_id in sids_after

        # cleanup
        _delete_contact(tokens["a"], ca["id"])


# ──────────────────────────────────────────────
# 執行入口
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
