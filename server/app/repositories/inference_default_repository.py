"""Repository for inference defaults (activity time, time of day, title patterns)."""

from typing import List, Optional
from sqlmodel import Session, select
from ..models.inference_default import InferenceDefault
import logging
logger = logging.getLogger(__name__)


# 程序內快取（同個 kind 不會變太頻繁）
_cache: dict[tuple[str, str], list] = {}


class InferenceDefaultRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, kind: str, keywords: List[str], result: str,
            fallback_result: Optional[str] = None, priority: int = 0,
            language: str = "zh-TW") -> InferenceDefault:
        item = InferenceDefault(
            kind=kind, keywords=keywords, result=result,
            fallback_result=fallback_result, priority=priority,
            language=language,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        _cache.clear()
        return item

    def add_batch(self, items: List[dict]) -> int:
        for it in items:
            self.session.add(InferenceDefault(
                kind=it["kind"],
                keywords=it["keywords"],
                result=it["result"],
                fallback_result=it.get("fallback_result"),
                priority=it.get("priority", 0),
                language=it.get("language", "zh-TW"),
            ))
        self.session.commit()
        _cache.clear()
        return len(items)

    def get_by_kind(self, kind: str, language: str = "zh-TW") -> List[InferenceDefault]:
        """Return all entries for a kind, sorted by priority desc."""
        key = (kind, language)
        if key in _cache:
            return _cache[key]
        rows = self.session.exec(
            select(InferenceDefault)
            .where(InferenceDefault.kind == kind)
            .where(InferenceDefault.language == language)
            .where(InferenceDefault.enabled == True)
            .order_by(InferenceDefault.priority.desc())
        ).all()
        _cache[key] = list(rows)
        return _cache[key]

    def find_match(self, kind: str, text: str, language: str = "zh-TW") -> Optional[InferenceDefault]:
        """
        Find first matching entry where any keyword appears in text.
        Returns None if no match.
        """
        for item in self.get_by_kind(kind, language):
            for kw in item.keywords:
                if kw in text:
                    return item
        return None


def get_defaults_dict(kind: str, language: str = "zh-TW") -> dict[str, str]:
    """
    便利函數：回傳 {keyword: result} dict。
    用在 prompt builder 等需要把所有 mapping 注入的地方。
    """
    try:
        from ..db.database import engine
        session = Session(engine)
        repo = InferenceDefaultRepository(session)
        items = repo.get_by_kind(kind, language)
        out = {}
        for item in items:
            for kw in item.keywords:
                out[kw] = item.result
        session.close()
        return out
    except Exception as e:
        logger.info(f"[InferenceDefault] Load failed for {kind}: {e}")
        return {}


def reload_inference_cache():
    _cache.clear()
