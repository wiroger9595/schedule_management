"""Lexicon — 關鍵字字典（不需向量，純鍵值對）。

替代 chat_utils.py 寫死的：
- NON_NAMES: 不是人名的常見詞（kind='non_name'）
- stop_words: 行程匹配時的停用詞（kind='stop_word'）
- edit_verb / create_verb / delete_verb: 動詞分類（未來擴充）
"""

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, DateTime, Integer, Boolean, Identity, UniqueConstraint
from datetime import datetime


class Lexicon(SQLModel, table=True):
    __tablename__ = "lexicon"
    __table_args__ = (
        UniqueConstraint("kind", "word", "language", name="uq_lexicon_kind_word_lang"),
    )

    id: int = Field(
        default=None,
        sa_column=Column(Integer, Identity(always=True), primary_key=True)
    )

    kind: str = Field(sa_column=Column(String(50), nullable=False))
    word: str = Field(sa_column=Column(String(100), nullable=False))
    language: str = Field(default="zh-TW", sa_column=Column(String(10), nullable=False))
    enabled: bool = Field(default=True, sa_column=Column(Boolean))

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
