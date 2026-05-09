"""Repository for prompt rules - dynamic prompt injection."""

from typing import List
from sqlmodel import Session, select
from ..models.prompt_rule import PromptRule
from ..services.embedding_service import EmbeddingService


class PromptRuleRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, topic: str, trigger_phrase: str, rule_text: str,
            priority: int = 0, language: str = "zh-TW") -> PromptRule:
        embedding = EmbeddingService.embed(trigger_phrase)
        rule = PromptRule(
            topic=topic,
            trigger_phrase=trigger_phrase,
            rule_text=rule_text,
            priority=priority,
            language=language,
            embedding=embedding,
        )
        self.session.add(rule)
        self.session.commit()
        self.session.refresh(rule)
        return rule

    def add_batch(self, items: List[dict]) -> int:
        """Each item: {topic, trigger_phrase, rule_text, priority?, language?}"""
        triggers = [it["trigger_phrase"] for it in items]
        embeddings = EmbeddingService.embed_batch(triggers)
        for it, emb in zip(items, embeddings):
            self.session.add(PromptRule(
                topic=it["topic"],
                trigger_phrase=it["trigger_phrase"],
                rule_text=it["rule_text"],
                priority=it.get("priority", 0),
                language=it.get("language", "zh-TW"),
                embedding=emb,
            ))
        self.session.commit()
        return len(items)

    def get_always_on(self, language: str = "zh-TW") -> List[PromptRule]:
        """Rules with priority >= 100 — always injected into prompt."""
        return self.session.exec(
            select(PromptRule)
            .where(PromptRule.language == language)
            .where(PromptRule.enabled == True)
            .where(PromptRule.priority >= 100)
            .order_by(PromptRule.priority.desc())
        ).all()

    def search_relevant(self, user_message: str, language: str = "zh-TW",
                        top_k: int = 5) -> List[PromptRule]:
        """Semantic search for top-k rules relevant to user message."""
        query_emb = EmbeddingService.embed(user_message)
        return self.session.exec(
            select(PromptRule)
            .where(PromptRule.language == language)
            .where(PromptRule.enabled == True)
            .where(PromptRule.priority < 100)  # only conditional rules
            .order_by(PromptRule.embedding.cosine_distance(query_emb))
            .limit(top_k)
        ).all()

    def count(self, language: str = "zh-TW") -> int:
        return len(self.session.exec(
            select(PromptRule).where(PromptRule.language == language)
        ).all())
