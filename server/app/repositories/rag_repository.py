"""Repository for RAG training examples."""

from typing import List
from sqlmodel import Session, select
from ..models.rag_example import RAGExample
from ..services.embedding_service import EmbeddingService


class RAGRepository:
    def __init__(self, session: Session):
        self.session = session
        self.embedding_service = EmbeddingService

    def add_example(
        self,
        language: str,
        category: str,
        user_message: str,
        intent: str,
        is_complete: bool = False,
        parsed_data: dict = None,
        context: dict = None,
    ) -> RAGExample:
        """Add a new RAG example with embedding."""
        embedding = self.embedding_service.embed(user_message)

        example = RAGExample(
            language=language,
            category=category,
            user_message=user_message,
            intent=intent,
            is_complete=is_complete,
            parsed_data=parsed_data or {},
            context=context or {},
            embedding=embedding,
        )
        self.session.add(example)
        self.session.commit()
        self.session.refresh(example)
        return example

    def add_batch(self, examples: List[dict], language: str = "zh-TW") -> int:
        """Bulk insert RAG examples with embeddings."""
        embedding_texts = [ex.get("user_message") for ex in examples]
        embeddings = self.embedding_service.embed_batch(embedding_texts)

        for ex, embedding in zip(examples, embeddings):
            rag_ex = RAGExample(
                language=language,
                category=ex.get("category", "general"),
                user_message=ex.get("user_message", ""),
                intent=ex.get("intent", "create"),
                is_complete=ex.get("is_complete", False),
                parsed_data=ex.get("parsed_data", {}),
                context=ex.get("context", {}),
                embedding=embedding,
            )
            self.session.add(rag_ex)

        self.session.commit()
        return len(examples)

    def search_similar(
        self,
        user_message: str,
        language: str = "zh-TW",
        intent: str = None,
        top_k: int = 5,
        query_embedding=None,
    ) -> List[RAGExample]:
        """Search similar examples using vector similarity."""
        if query_embedding is None:
            query_embedding = self.embedding_service.embed(user_message)

        stmt = select(RAGExample).where(RAGExample.language == language)
        if intent:
            stmt = stmt.where(RAGExample.intent == intent)

        # PgVector distance query (cosine similarity)
        # embedding <-> query_embedding gives distance, order by distance ascending
        stmt = stmt.order_by(
            RAGExample.embedding.cosine_distance(query_embedding)
        ).limit(top_k)

        return self.session.exec(stmt).all()

    def search_by_category(self, category: str, language: str = "zh-TW") -> List[RAGExample]:
        """Get all examples in a category."""
        stmt = select(RAGExample).where(
            (RAGExample.category == category) & (RAGExample.language == language)
        )
        return self.session.exec(stmt).all()

    def get_all_by_language(self, language: str) -> List[RAGExample]:
        """Get all examples for a language."""
        stmt = select(RAGExample).where(RAGExample.language == language)
        return self.session.exec(stmt).all()

    def count_by_language(self, language: str) -> int:
        """Count examples by language."""
        stmt = select(RAGExample).where(RAGExample.language == language)
        return len(self.session.exec(stmt).all())
