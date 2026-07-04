"""RAG / pgvector 整合測試——用真實 DB（CLAUDE.md：不 mock DB）。
DB 連不上時自動 skip。"""
import pytest
from sqlmodel import Session

from tests.conftest import db_required


@db_required
@pytest.mark.db
def test_rag_search_returns_relevant_intent():
    """「取消＋活動」類查詢必須檢索到 delete 例句（2026-07-04 修過的回歸測試）。"""
    from app.db.database import engine
    from app.repositories.rag_repository import RAGRepository
    from app.services.embedding_service import EmbeddingService

    with Session(engine) as session:
        repo = RAGRepository(session)
        emb = EmbeddingService.embed("取消打球")
        results = repo.search_similar("取消打球", top_k=3, query_embedding=emb)
        assert results, "應至少檢索到一筆案例"
        intents = [r.intent for r in results]
        assert intents.count("delete") >= 2, f"top-3 應多數為 delete，實際: {intents}"


@db_required
@pytest.mark.db
def test_rag_distance_threshold_blocks_irrelevant():
    """門檻應擋掉不相關案例：隨機亂字串不應撈到任何東西。"""
    from app.db.database import engine
    from app.repositories.rag_repository import RAGRepository
    from app.services.embedding_service import EmbeddingService

    with Session(engine) as session:
        repo = RAGRepository(session)
        query = "量子力學波函數坍縮的哥本哈根詮釋"
        emb = EmbeddingService.embed(query)
        results = repo.search_similar(query, top_k=5, query_embedding=emb)
        assert results == [], f"與行程無關的查詢不應注入案例，實際撈到 {len(results)} 筆"


@db_required
@pytest.mark.db
def test_rag_no_duplicate_examples():
    """例句庫不應有重複（同 user_message + intent）。"""
    from sqlalchemy import text
    from app.db.database import engine, postgres_schema as s

    with engine.connect() as conn:
        dup = conn.execute(text(f"""
            SELECT COUNT(*) FROM (
                SELECT 1 FROM {s}.rag_example
                GROUP BY user_message, intent HAVING COUNT(*) > 1
            ) t
        """)).scalar()
        assert dup == 0, f"發現 {dup} 組重複例句"
