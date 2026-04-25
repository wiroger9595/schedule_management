from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Integer, Identity, String, Boolean, Text, DateTime
from typing import Optional
from datetime import datetime


class AIFeedback(SQLModel, table=True):
    __tablename__ = "ai_feedback"
    __table_args__ = {"schema": "schedule_management"}

    id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, Identity(always=True), primary_key=True),
    )
    user_id: str = Field(sa_column=Column(String(255), nullable=False))
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow),
    )
    user_message: str = Field(sa_column=Column(Text, nullable=False))
    ai_reply: str = Field(sa_column=Column(Text, nullable=False))
    is_good: bool = Field(sa_column=Column(Boolean, nullable=False))
    correction: Optional[str] = Field(default=None, sa_column=Column(Text))
    conversation_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    model_label: Optional[str] = Field(default=None, sa_column=Column(String(128)))
