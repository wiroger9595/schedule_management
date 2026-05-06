"""
匯出 AI 訓練資料 → JSONL（OpenAI / Gemini fine-tuning 格式）

用法：
  python export_training_data.py                    # 匯出所有 is_good=True
  python export_training_data.py --min-id 100       # 從 id=100 開始
  python export_training_data.py --out data.jsonl   # 指定輸出檔案

輸出格式（OpenAI tool calling fine-tuning）：
  {"messages": [
    {"role": "system", "content": "..."},
    {"role": "user",   "content": "..."},
    {"role": "assistant", "content": null, "tool_calls": [{...}]}
  ]}
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta

# ── 載入環境變數 ──────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

# ── 精簡的 system prompt（不含動態行程清單，避免每筆不同）────────────────────
SYSTEM_PROMPT = (
    "你是行程規劃助理，專門幫用戶建立、修改、刪除行程。"
    "使用工具 create_schedule / update_schedule / delete_schedule / ask_user / reply_to_user。"
    "只做行程相關操作，回覆簡潔，只說做了什麼。"
)

TOOL_NAMES = {"create_schedule", "update_schedule", "delete_schedule", "ask_user", "reply_to_user"}


def build_messages(record) -> list | None:
    """從一筆 AIFeedback 記錄組成 fine-tuning messages list。"""
    try:
        ctx = json.loads(record.conversation_json) if record.conversation_json else {}
    except Exception:
        return None

    intent    = ctx.get("intent", "create")
    tool_call = ctx.get("tool_call", {})
    history   = ctx.get("history", [])

    fn_name = tool_call.get("name", "")
    fn_args = tool_call.get("args", {})

    if fn_name not in TOOL_NAMES:
        return None
    if not fn_args and fn_name not in ("reply_to_user",):
        return None

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 加最近 4 輪對話歷史（不含最後一輪，避免重複）
    for turn in history[-4:]:
        role    = turn.get("role", "")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    # 用戶最後一句
    messages.append({"role": "user", "content": record.user_message})

    # AI 正確的工具呼叫
    messages.append({
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_0",
            "type": "function",
            "function": {
                "name": fn_name,
                "arguments": json.dumps(fn_args, ensure_ascii=False),
            },
        }],
    })

    return messages


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out",     default="training_data.jsonl")
    parser.add_argument("--min-id",  type=int, default=0)
    parser.add_argument("--limit",   type=int, default=10000)
    args = parser.parse_args()

    # ── 連接 DB ───────────────────────────────────────────────────────────────
    from sqlmodel import create_engine, Session, select
    from app.models.ai_feedback import AIFeedback

    engine = create_engine(os.environ["DATABASE_URL"])

    with Session(engine) as session:
        stmt = (
            select(AIFeedback)
            .where(AIFeedback.is_good == True)
            .where(AIFeedback.conversation_json != None)
            .where(AIFeedback.id >= args.min_id)
            .order_by(AIFeedback.id)
            .limit(args.limit)
        )
        records = session.exec(stmt).all()

    print(f"[export] 找到 {len(records)} 筆 is_good=True 記錄")

    ok = skipped = 0
    with open(args.out, "w", encoding="utf-8") as f:
        for rec in records:
            msgs = build_messages(rec)
            if msgs is None:
                skipped += 1
                continue
            f.write(json.dumps({"messages": msgs}, ensure_ascii=False) + "\n")
            ok += 1

    print(f"[export] ✅ 寫出 {ok} 筆  跳過 {skipped} 筆 → {args.out}")
    if ok < 50:
        print(f"[export] ⚠️  建議至少 50 筆再進行 fine-tuning（目前 {ok} 筆）")


if __name__ == "__main__":
    main()
