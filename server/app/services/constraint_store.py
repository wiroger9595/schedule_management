"""
Persistent AI constraint store.

Every time the backend catches an AI error (wrong schedule_id, empty update,
attendee-only schedule, etc.) it calls record_error(). The next AI call loads
all active constraints and injects them into the system prompt, so the same
mistake never repeats.

Storage: JSON file (no DB migration needed, survives restarts).
Thread-safe via a threading.Lock.
"""

from __future__ import annotations
import json
import os
import threading
from datetime import datetime

_STORE_PATH = os.path.join(os.path.dirname(__file__), "../../ai_constraints.json")
_lock = threading.Lock()


# ── Known error types ────────────────────────────────────────────────────────
# Predefined constraints for errors we already know about.
# record_error() will upsert these (incrementing count) or add new ones.

KNOWN_CONSTRAINTS: dict[str, str] = {
    "wrong_schedule_id": (
        "update_schedule / delete_schedule 的 schedule_id 必須完全符合行程清單中現有的 id 字串，"
        "不可自行推測、縮短、或填入相似的 id。若不確定請呼叫 ask_user 列出清單讓用戶選擇。"
    ),
    "attendee_only_schedule": (
        "行程清單中可能包含其他人邀請您參加的行程（非您建立）。"
        "update_schedule / delete_schedule 只能操作您自己建立的行程，"
        "若用戶描述的是受邀行程，請告知無法修改並列出可編輯的行程。"
    ),
    "empty_update_schedule": (
        "呼叫 update_schedule 時必須至少帶入一個修改欄位（title/start_time/location 等）。"
        "若用戶尚未說明要改成什麼，請先用 ask_user 詢問新值，不可呼叫空的 update_schedule。"
    ),
    "missing_schedule_id_in_update": (
        "呼叫 update_schedule 時 schedule_id 是必填欄位，不可省略。"
        "必須先從行程清單確認目標行程的 id 再呼叫。"
    ),
    "created_instead_of_edited": (
        "當 context 中已有 _pending_edit_schedule_id 時，用戶的回覆是補充修改資訊，"
        "必須呼叫 update_schedule，絕對不可呼叫 create_schedule。"
    ),
    "location_in_time_only_edit": (
        "用戶只說改時間（如「改成三點」「改成明天」）時，update_schedule 只帶 start_time，"
        "不可把 context 裡的舊 location 複製進去。只改用戶明確說要改的欄位。"
    ),
    "ambiguous_target_no_list": (
        "當修改/刪除目標不明確，或清單中有多個可能符合的行程時，"
        "必須在 ask_user 的 question 中列出行程清單（1️⃣ 名稱 — 時間 — 地點），"
        "讓用戶選擇，不可直接猜測並操作。"
    ),
}


# ── Public API ───────────────────────────────────────────────────────────────

def record_error(error_type: str, example: str = "", custom_constraint: str = "") -> None:
    """Record an error occurrence. Thread-safe."""
    constraint = custom_constraint or KNOWN_CONSTRAINTS.get(error_type, error_type)
    with _lock:
        data = _load()
        for item in data:
            if item["type"] == error_type:
                item["count"] = item.get("count", 0) + 1
                item["last_seen"] = _now()
                if example:
                    item["last_example"] = example[:200]
                break
        else:
            data.append({
                "type": error_type,
                "constraint": constraint,
                "last_example": example[:200] if example else "",
                "count": 1,
                "first_seen": _now(),
                "last_seen": _now(),
                "active": True,
            })
        _save(data)
    print(f"[constraint_store] recorded: {error_type} (example={example[:80]!r})")


def get_active_constraints() -> list[str]:
    """Return constraint strings for injection into system prompt."""
    try:
        return [
            item["constraint"]
            for item in _load()
            if item.get("active", True) and item.get("constraint")
        ]
    except Exception:
        return []


def deactivate(error_type: str) -> None:
    """Manually disable a constraint (e.g., after the underlying bug is fixed)."""
    with _lock:
        data = _load()
        for item in data:
            if item["type"] == error_type:
                item["active"] = False
        _save(data)


def summary() -> list[dict]:
    """Return all constraints with metadata (for admin / debugging)."""
    return _load()


# ── Internal ─────────────────────────────────────────────────────────────────

def _load() -> list[dict]:
    try:
        with open(_STORE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(data: list[dict]) -> None:
    with open(_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
