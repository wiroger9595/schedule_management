from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Integer, Identity, String, Boolean, Text, DateTime, Float
from typing import Optional
from datetime import datetime
import os

_schema = os.getenv("POSTGRES_SCHEMA", "public")


class AITestResult(SQLModel, table=True):
    __tablename__ = "ai_test_result"
    __table_args__ = {"schema": _schema}

    id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, Identity(always=True), primary_key=True),
    )

    # Test case identifier
    test_case_id: str = Field(sa_column=Column(String(64), nullable=False))
    category: str = Field(sa_column=Column(String(32), nullable=False))

    # Expected values
    user_message: str = Field(sa_column=Column(Text, nullable=False))
    expected_intent: str = Field(sa_column=Column(String(32), nullable=False))
    expected_complete: bool = Field(sa_column=Column(Boolean, nullable=False))

    # Model info
    model_name: str = Field(sa_column=Column(String(128), nullable=False))

    # Actual values (model response)
    actual_intent: Optional[str] = Field(default=None, sa_column=Column(String(32)))
    actual_complete: Optional[bool] = Field(default=None, sa_column=Column(Boolean))
    model_reply: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Test result
    passed: bool = Field(sa_column=Column(Boolean, nullable=False))
    quality_score: float = Field(sa_column=Column(Float, nullable=False))
    duration_ms: float = Field(sa_column=Column(Float, nullable=False))

    # Errors
    errors: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime, default=datetime.utcnow),
    )
