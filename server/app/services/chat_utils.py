import re
from datetime import datetime
from typing import Optional

import arrow
from sqlmodel import select

from ..models.contact import Contact


def extract_person_hint(message: str) -> Optional[str]:
    NON_NAMES = {"我", "你", "他", "她", "他們", "大家", "朋友", "同事", "家人",
                 "老闆", "客戶", "你們", "我們"}
    patterns = [
        r'[與和跟找]([A-Za-z\u4e00-\u9fff]{1,6})(?:見面|開會|吃飯|談|碰面|的行程|的時間|的地點|的約)',
        r'[與和跟找]([A-Za-z\u4e00-\u9fff]{1,6})(?:\s|$|，|,|。|！|？)',
    ]
    for pat in patterns:
        m = re.search(pat, message)
        if m:
            name = m.group(1).strip()
            if name and name not in NON_NAMES:
                return name
    return None


def check_person_in_contacts(user_id: str, person_hint: str, session) -> bool:
    c = session.exec(
        select(Contact).where(
            Contact.user_id == user_id,
            Contact.nick_name.ilike(f"%{person_hint}%"),
        )
    ).first()
    return c is not None


def validate_output(data: dict, intent: str, session, user_id: str, current_context: dict) -> Optional[str]:
    start_str = data.get("start_time")
    end_str = data.get("end_time")
    if start_str:
        try:
            st = datetime.fromisoformat(start_str)
            if not (2024 <= st.year <= 2035):
                return f"行程時間 {st.year} 年看起來不對，請確認是否為 {datetime.now().year} 年？"
            if end_str:
                et = datetime.fromisoformat(end_str)
                if et <= st:
                    return "結束時間必須晚於開始時間，請確認時間是否正確？"
        except ValueError:
            return "時間格式無法解析，請重新說明行程時間。"

    parts = data.get("participants", [])
    if isinstance(parts, str):
        parts = [p.strip() for p in parts.split(",") if p.strip()]
    similar_map: dict[str, str] = {}
    for p in parts:
        clean = p.strip().lstrip("@")
        if not clean:
            continue
        exact = session.exec(
            select(Contact).where(Contact.user_id == user_id, Contact.nick_name == clean)
        ).first()
        if not exact:
            fuzzy = session.exec(
                select(Contact).where(
                    Contact.user_id == user_id,
                    Contact.nick_name.ilike(f"%{clean}%"),
                )
            ).first()
            if fuzzy:
                similar_map[clean] = fuzzy.nick_name

    if similar_map:
        suggestions = "、".join(f"@{k} → 是否為 @{v}？" for k, v in similar_map.items())
        return f"找不到完全符合的聯絡人，{suggestions}"

    if intent == "create" and not data.get("location"):
        return "請問行程地點在哪裡？"

    return None


def _to_taipei(dt) -> arrow.Arrow:
    """Convert datetime to Asia/Taipei Arrow. Naive datetimes are treated as Taiwan local time."""
    if dt is None:
        return None
    if hasattr(dt, 'tzinfo') and dt.tzinfo is None:
        return arrow.get(dt, "Asia/Taipei")
    return arrow.get(dt).to("Asia/Taipei")


def _display_hour(h: int) -> int:
    """Convert 24h hour to 12h Chinese display format (下午3點 instead of 下午15點)."""
    return h if h <= 12 else h - 12


def fmt_schedule_summary(obj) -> str:
    lines = [f"📋 行程名稱：{obj.title or '未命名'}"]
    if obj.meeting_start_time:
        _t = _to_taipei(obj.meeting_start_time)
        _h = _t.hour
        _p = ("上午" if 6 <= _h < 12 else "中午" if 12 <= _h < 14
              else "下午" if 14 <= _h < 18 else "晚上" if 18 <= _h < 22 else "深夜")
        _ts = f"{_t.month}月{_t.day}日（{_t.format('ddd', locale='zh_TW')}）{_p}{_display_hour(_h)}點"
        if getattr(obj, "meeting_end_time", None):
            _et = _to_taipei(obj.meeting_end_time)
            _ep = ("上午" if 6 <= _et.hour < 12 else "中午" if 12 <= _et.hour < 14
                   else "下午" if 14 <= _et.hour < 18 else "晚上" if 18 <= _et.hour < 22 else "深夜")
            _ts += f"到{'（' + _ep + '）' if _ep != _p else ''}{_display_hour(_et.hour)}點"
        lines.append(f"🕐 時間：{_ts}")
    if getattr(obj, "meeting_location", None):
        lines.append(f"📍 地點：{obj.meeting_location}")
    return "\n".join(lines)


def python_match_schedules(message: str, schedules: list) -> list:
    if not schedules:
        return schedules
    stop_words = {"取消", "刪除", "刪掉", "移除", "更改", "修改", "調整", "把", "的", "行程",
                  "活動", "我", "這個", "請", "幫我", "改到", "延後", "提早"}
    words = [w for w in message if w not in stop_words and len(w.strip()) > 0]
    keyword = "".join(words)

    tagged = []
    for s in schedules:
        title = s.get("title", "")
        matched = False
        for length in range(len(keyword), 1, -1):
            for start_idx in range(len(keyword) - length + 1):
                chunk = keyword[start_idx:start_idx + length]
                if len(chunk) >= 2 and chunk in title:
                    matched = True
                    break
            if matched:
                break
        if matched:
            s = dict(s)
            s["_match"] = True
        tagged.append(s)
    return tagged
