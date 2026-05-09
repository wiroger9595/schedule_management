from app.db.database import engine
from sqlalchemy import text

migrations = [
    "ALTER TABLE schedule_management.schedule ADD COLUMN IF NOT EXISTS is_online BOOLEAN DEFAULT FALSE;",
    "ALTER TABLE schedule_management.users ADD COLUMN IF NOT EXISTS fcm_token VARCHAR(512);",

    # ── pgvector: 語意搜尋行程 ────────────────────────────────────────────────
    # 1. 啟用 pgvector extension（Supabase 已內建，直接 CREATE EXTENSION）
    "CREATE EXTENSION IF NOT EXISTS vector;",

    # 2. 建立 embedding 儲存表（獨立於 schedule，避免影響現有 model）
    """
    CREATE TABLE IF NOT EXISTS schedule_management.schedule_embedding (
        schedule_id VARCHAR(255) PRIMARY KEY,
        embedding vector(512) NOT NULL,
        updated_at TIMESTAMP DEFAULT NOW()
    );
    """,

    # 3. HNSW index（取代 IVFFlat，召回率更高，不需預先指定 lists）
    "DROP INDEX IF EXISTS schedule_management.idx_schedule_embedding_cosine;",
    """
    CREATE INDEX IF NOT EXISTS idx_schedule_embedding_hnsw
    ON schedule_management.schedule_embedding
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
    """,

    # ── 聯絡人 embedding ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS schedule_management.contact_embedding (
        contact_id INT PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        embedding vector(512) NOT NULL,
        updated_at TIMESTAMP DEFAULT NOW()
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_contact_embedding_hnsw
    ON schedule_management.contact_embedding
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
    """,

    # ── AI 對話回饋（用於 fine-tune） ──────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS schedule_management.ai_feedback (
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
    """
    CREATE INDEX IF NOT EXISTS idx_ai_feedback_user_id
    ON schedule_management.ai_feedback (user_id);
    """,

    # ── 用戶偏好記憶 ──────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS schedule_management.user_memory (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        content TEXT NOT NULL,
        memory_type VARCHAR(50) DEFAULT 'general',
        embedding vector(512),
        created_at TIMESTAMP DEFAULT NOW()
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_user_memory_user_id
    ON schedule_management.user_memory (user_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_user_memory_hnsw
    ON schedule_management.user_memory
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
    """,

    # ── AI 測試結果（用於追踪模型改進） ──────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS schedule_management.ai_test_result (
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
    """
    CREATE INDEX IF NOT EXISTS idx_ai_test_result_category
    ON schedule_management.ai_test_result (category);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_ai_test_result_passed
    ON schedule_management.ai_test_result (passed);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_ai_test_result_model
    ON schedule_management.ai_test_result (model_name);
    """,

    # ── Intent 錨點（替代硬編碼的 INTENT_EXAMPLES） ───────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS schedule_management.intent_anchor (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        intent VARCHAR(50) NOT NULL,
        example VARCHAR(500) NOT NULL,
        language VARCHAR(10) NOT NULL DEFAULT 'zh-TW',
        embedding vector(512),
        enabled BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_intent_anchor_intent
    ON schedule_management.intent_anchor (intent);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_intent_anchor_lang
    ON schedule_management.intent_anchor (language);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_intent_anchor_embedding_hnsw
    ON schedule_management.intent_anchor
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
    """,

    # ── Prompt 規則（動態注入到 system prompt） ────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS schedule_management.prompt_rule (
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
    """
    CREATE INDEX IF NOT EXISTS idx_prompt_rule_topic
    ON schedule_management.prompt_rule (topic);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_prompt_rule_embedding_hnsw
    ON schedule_management.prompt_rule
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
    """,

    # ── App Config（運行時可調整的閾值與旗標）─────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS schedule_management.app_config (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        key VARCHAR(100) UNIQUE NOT NULL,
        value TEXT NOT NULL,
        value_type VARCHAR(20) NOT NULL DEFAULT 'str',
        description TEXT,
        updated_at TIMESTAMP DEFAULT NOW()
    );
    """,

    # ── Inference Default（AI 推斷預設值）─────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS schedule_management.inference_default (
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
    """
    CREATE INDEX IF NOT EXISTS idx_inference_default_kind
    ON schedule_management.inference_default (kind);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_inference_default_keywords
    ON schedule_management.inference_default USING gin (keywords);
    """,

    # ── Lexicon（關鍵字字典，stop_word/non_name/edit_verb 等）────────────────────
    """
    CREATE TABLE IF NOT EXISTS schedule_management.lexicon (
        id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        kind VARCHAR(50) NOT NULL,
        word VARCHAR(100) NOT NULL,
        language VARCHAR(10) NOT NULL DEFAULT 'zh-TW',
        enabled BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE (kind, word, language)
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_lexicon_kind_lang
    ON schedule_management.lexicon (kind, language);
    """,

    # ── RAG 訓練範例（用於檢索增強生成） ────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS schedule_management.rag_example (
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
    """
    CREATE INDEX IF NOT EXISTS idx_rag_example_language
    ON schedule_management.rag_example (language);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_rag_example_category
    ON schedule_management.rag_example (category);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_rag_example_intent
    ON schedule_management.rag_example (intent);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_rag_example_embedding_hnsw
    ON schedule_management.rag_example
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
    """,
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
