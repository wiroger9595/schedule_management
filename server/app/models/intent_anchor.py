"""Intent anchor — 語意路由的代表例句存到 DB（替代硬編碼 INTENT_EXAMPLES）。"""

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid


class IntentAnchor(SQLModel, table=True):
    __tablename__ = "intent_anchor"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True)
    )

    intent: str = Field(sa_column=Column(String(50), nullable=False))  # create/edit/delete/query
    example: str = Field(sa_column=Column(String(500), nullable=False))
    language: str = Field(default="zh-TW", sa_column=Column(String(10), nullable=False))
    embedding: list = Field(
        default=None,
        sa_column=Column(Vector(512), nullable=True),
    )
    enabled: bool = Field(default=True)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
