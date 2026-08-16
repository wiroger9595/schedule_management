from app.db.database import engine, postgres_schema
from sqlalchemy import text

s = postgres_schema  # short alias used in all SQL below

migrations = [
    f"ALTER TABLE {s}.schedule ADD COLUMN IF NOT EXISTS is_online BOOLEAN DEFAULT FALSE;",
    f"ALTER TABLE {s}.users ADD COLUMN IF NOT EXISTS fcm_token VARCHAR(512);",

    # ── 多設備 FCM token 管理 ──────────────────────────────────────────────────
    f"""
    CREATE TABLE IF NOT EXISTS {s}.user_devices (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        device_id VARCHAR(255) NOT NULL UNIQUE,
        platform VARCHAR(50) NOT NULL,
        fcm_token VARCHAR(512) NOT NULL,
        last_registered_at TIMESTAMPTZ DEFAULT NOW(),
        FOREIGN KEY (user_id) REFERENCES {s}.users(user_id) ON DELETE CASCADE
    );
    """,
    f"CREATE INDEX IF NOT EXISTS idx_user_devices_user_id ON {s}.user_devices(user_id);",

    # ── 提醒時間（根據交通工具計算的出發時間） ──────────────────────────────────
    f"ALTER TABLE {s}.schedule ADD COLUMN IF NOT EXISTS reminder_leave_by_time TIMESTAMPTZ;",

    # ── pgvector: 語意搜尋行程 ────────────────────────────────────────────────
    "CREATE EXTENSION IF NOT EXISTS vector;",

    f"""
    CREATE TABLE IF NOT EXISTS {s}.schedule_embedding (
        schedule_id VARCHAR(255) PRIMARY KEY,
        embedding vector(512) NOT NULL,
        updated_at TIMESTAMP DEFAULT NOW()
    );
    """,

    f"DROP INDEX IF EXISTS {s}.idx_schedule_embedding_cosine;",
    f"""
    CREATE INDEX IF NOT EXISTS idx_schedule_embedding_hnsw
    ON {s}.schedule_embedding
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
    """,

    # ── 聯絡人 embedding ──────────────────────────────────────────────────────
    f"""
    CREATE TABLE IF NOT EXISTS {s}.contact_embedding (
        contact_id INT PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        embedding vector(512) NOT NULL,
        updated_at TIMESTAMP DEFAULT NOW()
    );
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_contact_embedding_hnsw
    ON {s}.contact_embedding
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
    """,

    # ── AI 對話回饋（用於 fine-tune） ──────────────────────────────────────────
    f"""
    CREATE TABLE IF NOT EXISTS {s}.ai_feedback (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        user_message TEXT NOT NULL,
        ai_reply TEXT NOT NULL,
        is_good BOOLEAN NOT NULL,
        correction TEXT,
        conversation_json TEXT,
        model_label VARCHAR(128)
    );
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_ai_feedback_user_id
    ON {s}.ai_feedback (user_id);
    """,

    # ── 用戶偏好記憶 ──────────────────────────────────────────────────────────
    f"""
    CREATE TABLE IF NOT EXISTS {s}.user_memory (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        content TEXT NOT NULL,
        memory_type VARCHAR(50) DEFAULT 'general',
        embedding vector(512),
        created_at TIMESTAMP DEFAULT NOW()
    );
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_user_memory_user_id
    ON {s}.user_memory (user_id);
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_user_memory_hnsw
    ON {s}.user_memory
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
    """,

    # ── AI 測試結果（用於追踪模型改進） ──────────────────────────────────────────
    f"""
    CREATE TABLE IF NOT EXISTS {s}.ai_test_result (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        test_case_id VARCHAR(64) NOT NULL,
        category VARCHAR(32) NOT NULL,
        user_message TEXT NOT NULL,
        expected_intent VARCHAR(32) NOT NULL,
        expected_complete BOOLEAN NOT NULL,
        model_name VARCHAR(128) NOT NULL,
        actual_intent VARCHAR(32),
        actual_complete BOOLEAN,
        model_reply TEXT,
        passed BOOLEAN NOT NULL,
        quality_score FLOAT NOT NULL,
        duration_ms FLOAT NOT NULL,
        errors TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_ai_test_result_category
    ON {s}.ai_test_result (category);
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_ai_test_result_passed
    ON {s}.ai_test_result (passed);
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_ai_test_result_model
    ON {s}.ai_test_result (model_name);
    """,

    # ── Intent 錨點（替代硬編碼的 INTENT_EXAMPLES） ───────────────────────────────
    f"""
    CREATE TABLE IF NOT EXISTS {s}.intent_anchor (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        intent VARCHAR(50) NOT NULL,
        example VARCHAR(500) NOT NULL,
        language VARCHAR(10) NOT NULL DEFAULT 'zh-TW',
        embedding vector(512),
        enabled BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_intent_anchor_intent
    ON {s}.intent_anchor (intent);
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_intent_anchor_lang
    ON {s}.intent_anchor (language);
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_intent_anchor_embedding_hnsw
    ON {s}.intent_anchor
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
    """,

    # ── Prompt 規則（動態注入到 system prompt） ────────────────────────────────
    f"""
    CREATE TABLE IF NOT EXISTS {s}.prompt_rule (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        topic VARCHAR(100) NOT NULL,
        trigger_phrase TEXT NOT NULL,
        rule_text TEXT NOT NULL,
        priority INT DEFAULT 0,
        language VARCHAR(10) NOT NULL DEFAULT 'zh-TW',
        embedding vector(512),
        enabled BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_prompt_rule_topic
    ON {s}.prompt_rule (topic);
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_prompt_rule_embedding_hnsw
    ON {s}.prompt_rule
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
    """,

    # ── App Config（運行時可調整的閾值與旗標）─────────────────────────────────
    f"""
    CREATE TABLE IF NOT EXISTS {s}.app_config (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        key VARCHAR(100) UNIQUE NOT NULL,
        value TEXT NOT NULL,
        value_type VARCHAR(20) NOT NULL DEFAULT 'str',
        description TEXT,
        updated_at TIMESTAMP DEFAULT NOW()
    );
    """,

    # ── Inference Default（AI 推斷預設值）─────────────────────────────────────
    f"""
    CREATE TABLE IF NOT EXISTS {s}.inference_default (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        kind VARCHAR(50) NOT NULL,
        keywords TEXT[] NOT NULL,
        result VARCHAR(255) NOT NULL,
        fallback_result VARCHAR(255),
        priority INT DEFAULT 0,
        language VARCHAR(10) NOT NULL DEFAULT 'zh-TW',
        embedding vector(512),
        enabled BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_inference_default_kind
    ON {s}.inference_default (kind);
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_inference_default_keywords
    ON {s}.inference_default USING gin (keywords);
    """,

    # ── Lexicon（關鍵字字典，stop_word/non_name/edit_verb 等）────────────────────
    f"""
    CREATE TABLE IF NOT EXISTS {s}.lexicon (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        kind VARCHAR(50) NOT NULL,
        word VARCHAR(100) NOT NULL,
        language VARCHAR(10) NOT NULL DEFAULT 'zh-TW',
        enabled BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE (kind, word, language)
    );
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_lexicon_kind_lang
    ON {s}.lexicon (kind, language);
    """,

    # ── RAG 訓練範例（用於檢索增強生成） ────────────────────────────────────────────
    f"""
    CREATE TABLE IF NOT EXISTS {s}.rag_example (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        language VARCHAR(10) NOT NULL DEFAULT 'zh-TW',
        category VARCHAR(100) NOT NULL,
        user_message TEXT NOT NULL,
        context JSONB,
        intent VARCHAR(50) NOT NULL,
        is_complete BOOLEAN DEFAULT FALSE,
        parsed_data JSONB,
        embedding vector(512),
        created_at TIMESTAMP DEFAULT NOW()
    );
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_rag_example_language
    ON {s}.rag_example (language);
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_rag_example_category
    ON {s}.rag_example (category);
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_rag_example_intent
    ON {s}.rag_example (intent);
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_rag_example_embedding_hnsw
    ON {s}.rag_example
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
    """,

    # ── 業務表索引（熱路徑查詢，原本只有 PK 會全表掃描）───────────────────────
    # schedule：查「某用戶的行程」+ 按時間排序/篩選，composite 一次涵蓋
    f"""
    CREATE INDEX IF NOT EXISTS idx_schedule_user_start
    ON {s}.schedule (user_id, meeting_start_time);
    """,
    # attend：既有 unique 索引 leading column 是 attend_id，
    # 對 schedule_id / user_id 單獨查詢無效，需另建
    f"""
    CREATE INDEX IF NOT EXISTS idx_attend_schedule_id
    ON {s}.attend (schedule_id);
    """,
    f"""
    CREATE INDEX IF NOT EXISTS idx_attend_user_id
    ON {s}.attend (user_id);
    """,

    # ── 可調式提醒偏移量（開始前 / 出發前幾分鐘提醒，預設 60）──────────────────
    f"ALTER TABLE {s}.schedule ADD COLUMN IF NOT EXISTS reminder_before_start_minutes INTEGER DEFAULT 60;",
    f"ALTER TABLE {s}.schedule ADD COLUMN IF NOT EXISTS reminder_before_leave_minutes INTEGER DEFAULT 60;",

    # ── contact.user_id 索引（get_by_user_id 三表 join 熱路徑）──────────────────
    f"""
    CREATE INDEX IF NOT EXISTS idx_contact_user_id
    ON {s}.contact (user_id);
    """,

    # ── Schedule.status 統一為 mobile 認得的 'PD'（舊資料是 'P'，mobile 只認 'PD'）─
    f"ALTER TABLE {s}.schedule ALTER COLUMN status SET DEFAULT 'PD';",
    f"UPDATE {s}.schedule SET status = 'PD' WHERE status = 'P';",

    # ── 訂閱方案 + 用戶自帶 AI key（BYOK）──────────────────────────────────────
    f"ALTER TABLE {s}.users ADD COLUMN IF NOT EXISTS plan VARCHAR(20) DEFAULT 'free';",
    f"UPDATE {s}.users SET plan = 'free' WHERE plan IS NULL;",
    f"ALTER TABLE {s}.users ADD COLUMN IF NOT EXISTS plan_expires_at TIMESTAMPTZ;",
    f"ALTER TABLE {s}.users ADD COLUMN IF NOT EXISTS ai_base_url VARCHAR(500);",
    f"ALTER TABLE {s}.users ADD COLUMN IF NOT EXISTS ai_model VARCHAR(200);",
    f"ALTER TABLE {s}.users ADD COLUMN IF NOT EXISTS ai_api_key_enc VARCHAR(1000);",
]

with engine.connect() as conn:
    for sql in migrations:
        display = sql.strip().replace('\n', ' ')[:70]
        print(f"Running: {display}...")
        try:
            conn.execute(text(sql))
            conn.commit()
            print("  OK")
        except Exception as e:
            print(f"  Error (may already exist): {e}")
print("Migrations done.")
