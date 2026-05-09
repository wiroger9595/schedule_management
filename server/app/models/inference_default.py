"""
Inference default — AI 推斷預設值（取代寫死在 prompt 文字裡的 mapping）。

替代：
- 「吃飯→19:00, 開會→09:00...」活動時間預設
- 「晚上=19:00, 下午=14:00...」時段詞映射
- 「吃飯+人名→『與X吃飯』」title 生成模板

特點：
- 結構化（kind/keywords/result），可獨立 INSERT/UPDATE 一條
- 同一個 keyword 可有多個 kind（如「吃飯」既是 activity_time 也是 title_template）
- 支援多語言
- 可有 embedding 做模糊匹配（如用戶說「用餐」也應命中「吃飯」）
"""

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Identity
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid


class InferenceDefault(SQLModel, table=True):
    __tablename__ = "inference_default"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True)
    )

    # 種類：
    # 'activity_time' - 活動 → 預設時間 (吃飯 → 19:00)
    # 'tod_time'      - 時段詞 → 時間 (晚上 → 19:00)
    # 'title_template'- title 生成模板 (吃飯 → 「與{person}吃飯」或「聚餐」)
    # 'duration'      - 預設時長 (會議 → 1h, 電影 → 2.5h)
    kind: str = Field(sa_column=Column(String(50), nullable=False))

    # 觸發詞列表（同義詞合併）：例 ['吃飯','聚餐','晚餐','約飯']
    keywords: list = Field(sa_column=Column(ARRAY(String), nullable=False))

    # 結果值：時間 'HH:MM:SS'、duration '01:00:00'、title pattern '與{person}吃飯'
    result: str = Field(sa_column=Column(String(255), nullable=False))

    # 備用結果（如吃飯：有人名→「與X吃飯」，無人名→「聚餐」）
    fallback_result: str = Field(default=None, sa_column=Column(String(255), nullable=True))

    # 優先級：高的先嘗試（避免「吃飯」匹配到「下午茶」）
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
