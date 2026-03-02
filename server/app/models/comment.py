from sqlmodel import Field, SQLModel
from datetime import datetime, timezone
from typing import Optional

class Comment(SQLModel, table=True):
    __tablename__ = "comment"

    id: Optional[int] = Field(default=None, primary_key=True)
    comment_id: str = Field(index=True)
    comment_description: str
    user_id: str = Field(index=True)
    status: Optional[str] = Field(default="P", max_length=20)
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )
