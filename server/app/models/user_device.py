from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from typing import Optional


class UserDevice(SQLModel, table=True):
    __tablename__ = "user_devices"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    device_id: str = Field(unique=True)
    platform: str
    fcm_token: str = Field(max_length=512)
    last_registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
