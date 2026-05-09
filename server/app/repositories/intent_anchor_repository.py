"""Repository for intent anchors (replaces hardcoded INTENT_EXAMPLES)."""

from typing import List, Dict
from sqlmodel import Session, select
from ..models.intent_anchor import IntentAnchor
from ..services.embedding_service import EmbeddingService


class IntentAnchorRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, intent: str, example: str, language: str = "zh-TW") -> IntentAnchor:
        """Add a single anchor with its embedding."""
        embedding = EmbeddingService.embed(example)
        anchor = IntentAnchor(
            intent=intent,
            example=example,
            language=language,
            embedding=embedding,
        )
        self.session.add(anchor)
        self.session.commit()
        self.session.refresh(anchor)
        return anchor

    def add_batch(self, items: List[dict]) -> int:
        """Bulk insert. Each item: {intent, example, language?}."""
        texts = [it["example"] for it in items]
        embeddings = EmbeddingService.embed_batch(texts)
        for it, emb in zip(items, embeddings):
            self.session.add(IntentAnchor(
                intent=it["intent"],
                example=it["example"],
                language=it.get("language", "zh-TW"),
                embedding=emb,
            ))
        self.session.commit()
        return len(items)

    def get_all_by_language(self, language: str = "zh-TW") -> Dict[str, list]:
        """Return {intent: [(example, embedding), ...]} for active anchors."""
        rows = self.session.exec(
            select(IntentAnchor)
            .where(IntentAnchor.language == language)
            .where(IntentAnchor.enabled == True)
        ).all()
        out: Dict[str, list] = {}
        for r in rows:
            out.setdefault(r.intent, []).append({
                "example": r.example,
                "embedding": r.embedding,
            })
        return out

    def count(self) -> int:
        return len(self.session.exec(select(IntentAnchor)).all())
