"""RAG (Retrieval Augmented Generation) service for AI assistant."""

from typing import List, Optional
from sqlmodel import Session
from ..repositories.rag_repository import RAGRepository
from ..models.rag_example import RAGExample


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

        for i, ex in enumerate(examples, 1):
            # 強調 intent 與 is_complete
            complete_marker = "✅ True (可直接執行)" if ex.is_complete else "❌ False (需追問)"
            lines.append(f"\n### 案例 {i}: 「{ex.user_message}」")
            lines.append(f"  → intent = **{ex.intent}**")
            lines.append(f"  → is_complete = **{complete_marker}**")

            if ex.parsed_data:
                # 過濾掉內部欄位
                meaningful = {k: v for k, v in ex.parsed_data.items()
                              if not k.startswith("_") and v}
                if meaningful:
                    parts = [f"{k}={v}" for k, v in meaningful.items()]
                    lines.append(f"  → 提取: {', '.join(parts[:4])}")

                # 修正提示（從失敗案例生成的特別重要）
                if "_correction_note" in ex.parsed_data:
                    lines.append(f"  ⚠️ {ex.parsed_data['_correction_note']}")

        return "\n".join(lines)

    def should_use_rag(self, language: str = "zh-TW") -> bool:
        """Check if RAG is available and should be used."""
        count = self.repo.count_by_language(language)
        return count > 0


def get_rag_service(session: Session) -> RAGService:
    """Factory function for RAG service."""
    return RAGService(session)
