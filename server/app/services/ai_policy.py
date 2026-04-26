"""
AI Policy — single source of truth for all AI behavior rules.

Edit this file to customize:
  - Schedule-related keyword lists
  - Off-topic guard behavior
  - Standard redirect / error messages
  - Schedule list formatting
"""
from __future__ import annotations

# ─── On-topic keywords ────────────────────────────────────────────────────────
# If ANY of these appears in the user's message, it's considered schedule-related.
SCHEDULE_KEYWORDS: tuple[str, ...] = (
    "行程", "schedule", "時間", "地點", "地址", "會議", "約", "活動",
    "建立", "修改", "刪除", "新增", "取消", "提醒", "參與", "出席",
    "今天", "明天", "這週", "下週", "calendar", "meeting", "event",
)

# ─── Standard messages ────────────────────────────────────────────────────────
OFF_TOPIC_REDIRECT = (
    "我是行程規劃助理，專門幫您安排、修改和管理行程 📅 "
    "請問您有什麼行程需要規劃嗎？"
)

CANT_FIND_EDIT    = "請問您要修改哪個行程呢？"
CANT_FIND_DELETE  = "請問您要刪除哪個行程呢？"
CANT_FIND_GENERIC = "找不到行程，可以再描述一次嗎？"

# ─── Schedule list formatting ─────────────────────────────────────────────────
LIST_ICONS       = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
LIST_MAX_ITEMS   = 5
LIST_DEFAULT_SUFFIX = "請回覆數字或行程名稱。"

# ─── ask_user list-injection detection ───────────────────────────────────────
# If ask_user's question contains one of these keywords AND no numbered list
# the backend will inject the schedule list automatically.
CANT_FIND_KEYWORDS     = ("找不到", "哪個行程", "確認名稱", "請確認")
LIST_INDICATOR_CHARS   = ("1️⃣", "2️⃣", "①", "1.")


# ─── Functions ────────────────────────────────────────────────────────────────

def build_schedule_list_reply(
    prefix: str,
    schedule_list: list,
    suffix: str = LIST_DEFAULT_SUFFIX,
) -> str:
    """
    Return a numbered schedule list string ready to send to the user.
    Falls back to a '（目前沒有可用的行程）' suffix when the list is empty.
    """
    from .prompt_builder import _to_taipei

    lines: list[str] = []
    for i, s in enumerate(schedule_list[:LIST_MAX_ITEMS]):
        title = s.get("title", "")
        st    = s.get("meeting_start_time") or s.get("start_time", "")
        if st:
            try:
                a  = _to_taipei(st)
                st = a.format("MM/DD HH:mm") if a else st
            except Exception:
                pass
        loc = s.get("meeting_location") or s.get("location", "")
        lines.append(f"{LIST_ICONS[i]} {title} — {st} — {loc}")

    if not lines:
        return f"{prefix}（目前沒有可用的行程）"
    return f"{prefix}\n" + "\n".join(lines) + f"\n{suffix}"


def is_off_topic(user_message: str, reply_text: str = "") -> bool:
    """
    Return True when the user message has no schedule-related content
    AND the AI reply also doesn't redirect to scheduling.
    Used as a post-generation guard before returning reply_to_user responses.
    """
    if not user_message or len(user_message.strip()) <= 1:
        return False
    if any(k in user_message for k in SCHEDULE_KEYWORDS):
        return False
    if reply_text and (
        "行程" in reply_text
        or "規劃" in reply_text
        or "schedule" in reply_text.lower()
        or "planning" in reply_text.lower()
    ):
        return False
    return True


def needs_list_injection(question: str) -> bool:
    """
    Return True when ask_user's question implies 'can't find the schedule'
    but doesn't include a numbered list — the schedule list should be injected.
    """
    has_list      = any(c in question for c in LIST_INDICATOR_CHARS)
    has_cant_find = any(k in question for k in CANT_FIND_KEYWORDS)
    return has_cant_find and not has_list


def build_inline_list(schedule_list: list, verb: str = "操作") -> str:
    """
    Build the full 'pick a schedule' reply for use inside ai_service fallback
    handlers (force-list after bad schedule_id, ask_user injection, etc.).
    """
    prefix = f"請問您要{verb}哪個行程呢？"
    return build_schedule_list_reply(prefix, schedule_list)
