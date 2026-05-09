"""Prompt rule — 動態注入到 system prompt 的規則（替代硬編碼）。"""

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid


class PromptRule(SQLModel, table=True):
    __tablename__ = "prompt_rule"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True)
    )

    # 主題（用於分類和除錯，e.g. "past_schedule", "location_chain", "title"）
    topic: str = Field(sa_column=Column(String(100), nullable=False))

    # 觸發短語（會被 embed，用戶 message 與此語意相近時注入此規則）
    trigger_phrase: str = Field(sa_column=Column(Text, nullable=False))

    # 實際規則內容（會直接拼進 prompt）
    rule_text: str = Field(sa_column=Column(Text, nullable=False))

    # 優先級：>= 100 = 永遠注入；< 100 = 按相似度檢索
    priority: int = Field(default=0, sa_column=Column(Integer))

    language: str = Field(default="zh-TW", sa_column=Column(String(10), nullable=False))
    embedding: list = Field(
        default=None,
        sa_column=Column(Vector(512), nullable=True),
    )
    enabled: bool = Field(default=True, sa_column=Column(Boolean))

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
