"""Repository for lexicon (keyword dictionaries)."""

from typing import Set, List
from sqlmodel import Session, select
from ..models.lexicon import Lexicon


# 程序內快取（避免每次查詢都打 DB）
_cache: dict[tuple[str, str], Set[str]] = {}


class LexiconRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_batch(self, kind: str, words: List[str], language: str = "zh-TW") -> int:
        """Bulk insert. Skips duplicates due to unique constraint."""
        n = 0
        for word in words:
            try:
                self.session.add(Lexicon(kind=kind, word=word, language=language))
                self.session.commit()
                n += 1
            except Exception:
                self.session.rollback()  # duplicate, skip
        # 清快取
        _cache.pop((kind, language), None)
        return n

    def get_set(self, kind: str, language: str = "zh-TW") -> Set[str]:
        """Return set of words for given kind. Cached in memory."""
        key = (kind, language)
        if key in _cache:
            return _cache[key]

        rows = self.session.exec(
            select(Lexicon.word)
            .where(Lexicon.kind == kind)
            .where(Lexicon.language == language)
            .where(Lexicon.enabled == True)
        ).all()
        result = set(rows)
        _cache[key] = result
        return result

    def reload_cache(self):
        """Clear cache. Call after INSERTing new lexicon entries."""
        _cache.clear()


def get_lexicon(kind: str, language: str = "zh-TW") -> Set[str]:
    """
    便利函數：直接取得 lexicon set，不用建 repo。
    用在 chat_utils.py 等沒有 session 的地方。
    """
    key = (kind, language)
    if key in _cache:
        return _cache[key]

    try:
        from ..db.database import engine
        session = Session(engine)
        repo = LexiconRepository(session)
        result = repo.get_set(kind, language)
        session.close()
        return result
    except Exception as e:
        print(f"[Lexicon] Load failed for {kind}: {e}")
        return set()


def reload_lexicon_cache():
    """Public function: clear all lexicon caches."""
    _cache.clear()
