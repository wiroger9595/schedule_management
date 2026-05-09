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
    ) -> List[RAGExample]:
        """Retrieve most relevant training examples for a user message."""
        return self.repo.search_similar(
            user_message=user_message,
            language=language,
            intent=intent,
            top_k=top_k,
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
            lines.append("## 相似的成功案例（供參考）:")
        else:
            lines.append("## Similar successful examples (for reference):")

        for i, ex in enumerate(examples, 1):
            lines.append(f"\n### 案例 {i}:")
            lines.append(f"**用戶**: {ex.user_message}")
            lines.append(f"**意圖**: {ex.intent}")
            lines.append(f"**完整**: {ex.is_complete}")

            if ex.parsed_data:
                lines.append("**提取結果**:")
                for key, value in ex.parsed_data.items():
                    lines.append(f"  - {key}: {value}")

        return "\n".join(lines)

    def should_use_rag(self, language: str = "zh-TW") -> bool:
        """Check if RAG is available and should be used."""
        count = self.repo.count_by_language(language)
        return count > 0


def get_rag_service(session: Session) -> RAGService:
    """Factory function for RAG service."""
    return RAGService(session)
