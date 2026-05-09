"""App config — 簡單的 key/value 儲存運行時可調整的閾值與旗標。

替代散落各處的 magic number：
- CONFIDENCE_THRESHOLD = 0.45（semantic_router_service.py）
- _FAILURE_COOLDOWN_SEC = 300（embedding_service.py）
- 2024-2035 year range（chat_utils.py validate_output）
- top_k=5 RAG retrieval, priority>=100 always-on, etc.
"""

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, DateTime, Integer, Identity, Text
from datetime import datetime


class AppConfig(SQLModel, table=True):
    __tablename__ = "app_config"

    id: int = Field(
        default=None,
        sa_column=Column(Integer, Identity(always=True), primary_key=True)
    )

    # 鍵值，全域唯一。命名建議：<module>.<param>，如 'semantic_router.confidence_threshold'
    key: str = Field(sa_column=Column(String(100), unique=True, nullable=False))

    # 值（字串儲存，依 value_type 解析）
    value: str = Field(sa_column=Column(Text, nullable=False))

    # 'float' / 'int' / 'str' / 'bool' / 'json'
    value_type: str = Field(default="str", sa_column=Column(String(20), nullable=False))

    # 描述（給人看的，方便日後查找）
    description: str = Field(default="", sa_column=Column(Text, nullable=True))

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
