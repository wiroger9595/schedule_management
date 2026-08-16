"""
種子資料：把散落各處的閾值與旗標寫入 app_config 表。

寫入後可以這樣動態調整（不用改 code、不用重啟）：
    UPDATE app_config SET value = '0.5' WHERE key = 'semantic_router.confidence_threshold';
    -- 等 60s 快取過期，或呼叫 config_reload()

讀取方式：
    from app.services.config_service import config_get
    threshold = config_get('semantic_router.confidence_threshold', default=0.45)
"""
import sys
import os
from dotenv import load_dotenv
load_dotenv()

from sqlmodel import Session
from sqlalchemy import text
from app.db.database import engine
from app.services.config_service import config_set, config_reload


CONFIGS = [
    # ── Semantic Router ────────────────────────────────────────────────
    ("semantic_router.confidence_threshold", "0.45", "float",
     "低於此值不預判 intent 交給 AI（範圍 0.0~1.0，越高越嚴格）"),

    # ── Embedding Cascade ──────────────────────────────────────────────
    ("embedding.failure_cooldown_sec", "300", "int",
     "embedding provider 失敗後 cooldown 秒數（rate limit/auth）"),

    # ── Validation ─────────────────────────────────────────────────────
    ("validation.year_min", "2024", "int",
     "行程時間最小年份"),
    ("validation.year_max", "2035", "int",
     "行程時間最大年份"),

    # ── RAG Retrieval ──────────────────────────────────────────────────
    ("rag.retrieve_top_k", "3", "int",
     "RAG 檢索的相似範例數量（5→3：repo 端已有 max_distance 擋低相關，多送純燒 token）"),
    ("rag.prompt_rule_top_k", "3", "int",
     "prompt_rule 檢索的條件規則數量"),
    ("rag.always_on_priority_threshold", "100", "int",
     "prompt_rule priority >= 此值會永遠注入"),

    # ── AI Service ─────────────────────────────────────────────────────
    ("ai_service.rate_limit_retry_sleep_sec", "15", "int",
     "Cerebras 等主力模型 rate limit 後重試前等待秒數"),
    ("ai_service.conversation_history_limit", "8", "int",
     "送給 AI 的歷史訊息最大筆數（20→8：行程對話幾乎不超過 4 輪就結束）"),
    ("ai_service.tool_trim_threshold", "0.65", "float",
     "語意路由信心 >= 此值才只送該 intent 的 tool schema；低於此值送全部。"
     "比 semantic_router.confidence_threshold 高一階，因為判錯會直接沒工具可用"),
]


def reset_table():
    schema = os.getenv("POSTGRES_SCHEMA", "public")
    session = Session(engine)
    session.execute(text(f"DELETE FROM {schema}.app_config"))
    session.commit()
    session.close()
    print("🗑️  Cleared app_config table")


def seed():
    for key, value, value_type, desc in CONFIGS:
        config_set(key, value, value_type, desc)
        print(f"  ✓ {key} = {value} ({value_type})")
    config_reload()
    print(f"\n✅ Inserted/updated {len(CONFIGS)} config entries")


def main():
    if "--reset" in sys.argv:
        reset_table()
    seed()
    print("\n調整方式：")
    print("  UPDATE app_config SET value = '...' WHERE key = '...';")
    print("  → 60 秒內自動生效（cache TTL）")


if __name__ == "__main__":
    main()
