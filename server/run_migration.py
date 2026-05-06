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
