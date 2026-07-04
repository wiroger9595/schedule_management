"""
Pytest 共用設定。

原則（CLAUDE.md）：不 mock DB。需要 DB 的測試標記 @pytest.mark.db，
DB 連不上時自動 skip（CI 沒起 postgres 也不會炸）。
"""
import pytest
from dotenv import load_dotenv

load_dotenv()


def _db_available() -> bool:
    try:
        from sqlalchemy import text
        from app.db.database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# 供 @pytest.mark.db 測試用：DB 不可用就整批 skip
db_required = pytest.mark.skipif(
    not _db_available(), reason="PostgreSQL 未啟動或連線失敗"
)
