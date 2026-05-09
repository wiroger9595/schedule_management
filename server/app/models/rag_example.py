from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, VECTOR
from datetime import datetime
import uuid

class RAGExample(SQLModel, table=True):
    __tablename__ = "rag_example"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True)
    )

    language: str = Field(default="zh-TW", sa_column=Column(String(10), nullable=False))
    category: str = Field(sa_column=Column(String(100), nullable=False))
    user_message: str = Field(sa_column=Column(Text, nullable=False))

    # RAG context data
    context: dict = Field(default={}, sa_column=Column(JSON, nullable=True))

    # Expected output
    intent: str = Field(sa_column=Column(String(50), nullable=False))
    is_complete: bool = Field(default=False)
    parsed_data: dict = Field(default={}, sa_column=Column(JSON, nullable=True))

    # Embedding vector (512-dim, matches existing schema)
    embedding: list = Field(
        default=None,
        sa_column=Column(VECTOR(512), nullable=True),
        description="512-dim embedding (Gemini text-embedding-004 / HF bge truncated)"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
