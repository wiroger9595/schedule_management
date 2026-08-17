"""
Prompt builder — 從 DB 動態組裝 system prompt。

架構：
- 核心骨架（角色、現在時間、上下文）寫在 code 裡，因為這些每次都要
- 規則段落從 prompt_rule 表載入：
  • priority >= 100 = 永遠注入
  • priority <  100 = 按用戶訊息相似度檢索 top-3 注入

加新規則 = INSERT 進 prompt_rule 表，不用改 code。
"""
from datetime import datetime
from typing import Optional

import arrow
import logging
logger = logging.getLogger(__name__)


def _to_taipei(dt) -> Optional["arrow.Arrow"]:
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return None
    if hasattr(dt, "tzinfo") and dt.tzinfo is None:
        return arrow.get(dt, "Asia/Taipei")
    return arrow.get(dt).to("Asia/Taipei")


# 每種 intent 真正需要看到幾筆行程：
# create 只是拿來擋撞期/重複建立，edit/delete 要能對到目標，query 要完整清單。
# 一筆約 25~40 tokens，從固定 20 筆縮下來對 create 是實打實的省。
_LIST_CAP_BY_INTENT = {"create": 8, "edit": 12, "delete": 12, "query": 20}


def build_schedule_section(schedule_list: Optional[list],
                           intent: Optional[str] = None) -> str:
    if not schedule_list:
        return "【行程清單】（未提供）"

    cap = _LIST_CAP_BY_INTENT.get(intent or "", 20)
    visible = schedule_list[:20]
    if len(visible) > cap:
        # 關鍵字命中的一定要留（AI 靠它認 edit/delete 目標），其餘按原順序補滿。
        keep = {i for i, s in enumerate(visible) if s.get("_match")}
        for i in range(len(visible)):
            if len(keep) >= cap:
                break
            keep.add(i)
        visible = [s for i, s in enumerate(visible) if i in keep]

    lines = []
    pre_matched = []
    for s in visible:
        sid = s.get("schedule_id") or s.get("id", "")
        title = s.get("title", "")
        st = s.get("meeting_start_time") or s.get("start_time", "")
        if st:
            try:
                _a = _to_taipei(st)
                st = _a.format("MM/DD HH:mm") if _a else st
            except Exception:
                pass
        loc = s.get("meeting_location") or s.get("location", "")
        is_match = s.get("_match", False)
        is_owner = s.get("is_owner", True)
        creator = s.get("creator_name") or ""
        owner_tag = "" if is_owner else f" 【{creator}建立，唯讀】"
        tag = "  ★" if is_match else "  "
        lines.append(f"{tag}id={sid} | {title} | {st} | {loc}{owner_tag}")
        if is_match:
            pre_matched.append(f"id={sid}（{title}）")
    section = "【行程清單】\n" + "\n".join(lines)
    if pre_matched:
        section += f"\n⚠️ 關鍵字匹配：{', '.join(pre_matched)} → edit/delete 直接用此 id"
    return section


def build_context_sections(contacts: list, memory: list, context: dict) -> tuple[str, str]:
    memory_section = ""
    if memory:
        lines = [f"  • {m['content']}" for m in memory[:4]]
        memory_section = "\n## 用戶個人偏好記憶（根據過去行程學習）\n" + "\n".join(lines)

    contact_section = ""
    if contacts:
        lines = [
            f"  • @{c['nick_name']}（相似度 {c['similarity']}）{' — ' + c['comment'] if c.get('comment') else ''}"
            for c in contacts[:5]
        ]
        contact_section = ("\n## 語意匹配到的聯絡人\n" + "\n".join(lines)
                           + "\n（以上是聯絡人名單，用於識別句子中的人名）")

    dup_keys = [k for k in context if k.startswith("_dup_")]
    if dup_keys:
        dup_lines = []
        for dk in dup_keys:
            dname = dk[5:]
            entries = context[dk]
            desc = "、".join(
                f"{'備註:' + e['comment'] if e['comment'] else ''}{'末4碼:' + e['phone'] if e['phone'] else '（無備註）'}"
                for e in entries
            )
            dup_lines.append(f"  ⚠️ @{dname} 有 {len(entries)} 位同名聯絡人：{desc}")
        contact_section += (
            "\n## ⚠️ 同名聯絡人（必須先問清楚是哪一位）\n" + "\n".join(dup_lines)
            + "\n→ 遇到同名聯絡人時，呼叫 ask_user 讓用戶說明是哪一位（用備註或電話末4碼區分）"
        )

    return contact_section, memory_section


def _load_rules_from_db(user_message: str = "", language: str = "zh-TW",
                        session=None, query_embedding=None) -> tuple[str, str]:
    """
    從 DB 載入適用的 prompt rules，回傳 (always_on, conditional)。

    刻意拆成兩份而不是接成一串：always_on 每次都一樣、conditional 每則訊息
    都不同，接在一起會讓固定的那半也跟著失去 prefix cache。
    """
    if not session:
        return "", ""

    try:
        from ..repositories.prompt_rule_repository import PromptRuleRepository
        repo = PromptRuleRepository(session)

        # Always-on rules
        always_on = repo.get_always_on(language=language)

        # Conditional rules (only if user message is present)
        conditional = []
        if user_message:
            conditional = repo.search_relevant(
                user_message=user_message, language=language, top_k=3,
                query_embedding=query_embedding,
            )

        return ("\n\n".join(r.rule_text for r in always_on),
                "\n\n".join(r.rule_text for r in conditional))

    except Exception as e:
        logger.info(f"[PromptBuilder] Rule loading failed (non-critical): {e}")
        return "", ""


def _load_inference_defaults(language: str = "zh-TW") -> str:
    """
    從 inference_default 表載入活動/時段/title 預設映射，組成 markdown 注入 prompt。
    取代之前寫死在 prompt_rule rule_text 裡的「吃飯→19:00, 開會→09:00...」文字。

    這裡不另外加快取：InferenceDefaultRepository 已經有一層永久快取，靠
    reload_inference_cache() 明確失效。在上面疊 TTL 快取會讓那個失效路徑失靈。
    """
    try:
        from ..repositories.inference_default_repository import InferenceDefaultRepository
        from ..db.database import engine

        local_session = Session(engine)
        repo = InferenceDefaultRepository(local_session)

        # 各類映射
        activity_time = repo.get_by_kind("activity_time", language)
        tod_time      = repo.get_by_kind("tod_time", language)
        title_tmpl    = repo.get_by_kind("title_template", language)
        duration      = repo.get_by_kind("duration", language)
        local_session.close()

        sections = []

        # 1. 活動 → 預設時間
        if activity_time:
            entries = []
            for d in activity_time:
                kws = "/".join(d.keywords[:3])  # 顯示前 3 個關鍵字
                entries.append(f"{kws}={d.result[:5]}")  # HH:MM only
            sections.append("## 活動預設時間\n- " + "; ".join(entries))

        # 2. 時段詞 → 時間
        if tod_time:
            entries = [f"{'/'.join(d.keywords[:2])}={d.result[:5]}" for d in tod_time]
            sections.append("## 時段詞預設\n- " + " ".join(entries) + "（直接用，不追問）")

        # 3. Title 生成模板
        if title_tmpl:
            lines = []
            for d in title_tmpl[:8]:  # 只取前 8 個避免太長
                kws = "/".join(d.keywords[:2])
                lines.append(f"  {kws} + 人名 → 「{d.result}」；無人名 → 「{d.fallback_result}」")
            sections.append("## Title 模板\n" + "\n".join(lines))

        # 4. 預設時長
        if duration:
            entries = []
            for d in duration:
                kws = "/".join(d.keywords[:2])
                hms = d.result[:5]  # HH:MM
                entries.append(f"{kws}={hms}")
            sections.append("## 預設時長 (end_time = start + duration)\n- " + "; ".join(entries))

        return "\n\n".join(sections) if sections else ""

    except Exception as e:
        logger.info(f"[PromptBuilder] Inference defaults load failed: {e}")
        return ""


# 需要 Session import
from sqlmodel import Session


def build_system_prompt(today: datetime, schedule_section: str,
                        memory_section: str, contact_section: str,
                        rag_section: str = "",
                        user_message: str = "",
                        session=None,
                        query_embedding=None) -> str:
    """
    組裝 system prompt。

    新增 user_message 和 session 參數：
    - user_message: 用於檢索相關 prompt rules
    - session: DB session 用於查詢規則

    若 session=None 或 DB 沒規則 → fallback 到最小 prompt（仍可運作）。
    """
    today_str = today.strftime("%Y-%m-%d %A")

    # ── Inject learned constraints (auto-accumulated from past errors) ────────
    _error_section = ""
    try:
        from .constraint_store import get_active_constraints
        _constraints = get_active_constraints()
        if _constraints:
            _lines = "\n".join(f"❌ 禁止：{c}" for c in _constraints)
            _error_section = f"\n\n## 🚫 已記錄的錯誤模式（絕對禁止重複，每次呼叫工具前必須逐條確認）\n{_lines}"
    except Exception:
        pass

    rag_note = f"\n\n{rag_section}" if rag_section else ""

    # ── Load rules from DB（動態 prompt 規則）─────────────────────────────
    always_rules, conditional_rules = _load_rules_from_db(
        user_message=user_message,
        language="zh-TW",
        session=session,
        query_embedding=query_embedding,
    )

    # ── Load inference defaults（活動時間/時段/title 等映射）──────────────
    inference_defaults = _load_inference_defaults(language="zh-TW")

    # 若 DB 沒規則（首次啟動或 DB 未種子）→ 使用 fallback 最小規則
    if not always_rules and not conditional_rules:
        always_rules = _FALLBACK_RULES

    inference_section = f"\n\n{inference_defaults}" if inference_defaults else ""
    conditional_section = f"\n\n{conditional_rules}" if conditional_rules else ""

    # ── 排列順序＝prefix cache 命中率 ────────────────────────────────────────
    # Cerebras 會回報 cached_tokens，代表 prefix cache 是真的有在算。
    # 前綴一旦分岔，後面全部重算，所以由「越少變的放越前面」排：
    #   靜態（角色/常駐規則/推論預設）
    #   → 半靜態（錯誤約束、用戶記憶）
    #   → 每則都變（現在時間、行程清單、語意匹配到的聯絡人、條件規則、RAG）
    # 時間特別要注意：精確到分鐘，放前面等於每分鐘把整個 prompt 前綴打掉一次。
    return f"""你是行程規劃助理，專門幫用戶建立、修改、刪除、查詢行程。請用與用戶相同的語言回覆。

{always_rules}{inference_section}{_error_section}{memory_section}

現在時間（台灣）：{today.strftime("%Y-%m-%d %H:%M")}（{today_str}）

{schedule_section}{contact_section}{conditional_section}{rag_note}"""


# ============================================================
# Fallback：DB 沒資料時使用，避免服務中斷
# ============================================================

_FALLBACK_RULES = """## Intent 識別
- create: 安排/約/邀請/新增/建立 → 建立新行程
- edit: 改/更改/改成/改到/換 + 清單中有此行程
- delete: 刪除/取消/去掉/不要 + 清單中有此行程
- query: 有什麼行程/列出/查詢 → 只回覆現狀

## 工具
- create_schedule(title, start_time, end_time, location, participants=[], reply): 必須齊全
- update_schedule(schedule_id, [改的欄位], reply): 只帶用戶要改的
- delete_schedule(schedule_id, reply)
- ask_user(question, partial_data={}): 缺資訊時用，partial_data 必須含目前已知所有欄位
- reply_to_user(message): 純對話/查詢

## 必要規則
- 個人行程需 title+time+location；多人會議需加 participants
- 過期行程改時間 → ask_user 追問新日期
- title 不含地點時間
- 參與者一律加 @
- 用戶只說時間 → 從清單取原始日期，禁止用今天日期覆蓋
- 每次只能新增或修改一個行程；若用戶同時要求多個，ask_user 告知「每次只能操作一個行程，請一個一個來」
"""
