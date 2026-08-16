"""RAG (Retrieval Augmented Generation) service for AI assistant."""

import time
from typing import List, Optional
from sqlmodel import Session
from ..repositories.rag_repository import RAGRepository
from ..models.rag_example import RAGExample

# 例句庫數量快取：{language: (count, cached_at)}。例句庫變動頻率極低，
# 不需要每則訊息都 COUNT 一次。
_rag_count_cache: dict[str, tuple[int, float]] = {}
_RAG_COUNT_TTL_SEC = 300


class RAGService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = RAGRepository(session)

    def get_relevant_examples(
        self,
        user_message: str,
        language: str = "zh-TW",
        intent: Optional[str] = None,
        top_k: int = 5,
        query_embedding: Optional[List[float]] = None,
    ) -> List[RAGExample]:
        """Retrieve most relevant training examples for a user message.

        If query_embedding is provided, skip re-embedding (used for caching across
        multiple retrievals with same query)."""
        return self.repo.search_similar(
            user_message=user_message,
            language=language,
            intent=intent,
            top_k=top_k,
            query_embedding=query_embedding,
        )

    def format_examples_for_prompt(
        self,
        examples: List[RAGExample],
        language: str = "zh-TW",
    ) -> str:
        """Format examples as part of system prompt."""
        if not examples:
            return ""

        lines = []
        if language == "zh-TW":
            lines.append("## 🎯 相似案例（請仔細對照判斷 intent 和 is_complete）:")
            lines.append("⚠️ 特別注意 is_complete：個人行程不需 participants；多人會議需 title+time+location+participants")
        else:
            lines.append("## 🎯 Similar examples (carefully match intent and is_complete):")
            lines.append("⚠️ Note is_complete: personal events don't need participants; meetings need title+time+location+participants")

        # 一例一行。原本一例攤成 4~6 行（標題、intent、is_complete、提取各一行），
        # 五例就吃掉快 900 tokens，但模型需要的訊息量其實一行就裝得下。
        for ex in examples:
            parts = [f"「{ex.user_message}」→ {ex.intent}",
                     f"complete={'T' if ex.is_complete else 'F'}"]

            if ex.parsed_data:
                meaningful = {k: v for k, v in ex.parsed_data.items()
                              if not k.startswith("_") and v}
                if meaningful:
                    kv = [f"{k}={v}" for k, v in list(meaningful.items())[:4]]
                    parts.append(" ".join(kv))

                # 修正提示（從失敗案例生成的特別重要），不省
                note = ex.parsed_data.get("_correction_note")
                if note:
                    parts.append(f"⚠️ {note}")

            lines.append("- " + " | ".join(parts))

        return "\n".join(lines)

    def should_use_rag(self, language: str = "zh-TW") -> bool:
        """Check if RAG is available and should be used (count 快取 5 分鐘)."""
        cached = _rag_count_cache.get(language)
        if cached and (time.time() - cached[1]) < _RAG_COUNT_TTL_SEC:
            return cached[0] > 0
        count = self.repo.count_by_language(language)
        _rag_count_cache[language] = (count, time.time())
        return count > 0


def get_rag_service(session: Session) -> RAGService:
    """Factory function for RAG service."""
    return RAGService(session)
