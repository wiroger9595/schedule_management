from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserRead(BaseModel):
    user_id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    line_id: Optional[str] = None
    profile_image_path: Optional[str] = None
    public_id: Optional[str] = None
    language: Optional[str] = None
    status: str = "Y"
    default_sending: Optional[str] = None
    line_user_id: Optional[str] = None
    fcm_token: Optional[str] = None
    google_id: Optional[str] = None
    apple_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    line_id: Optional[str] = None
    language: Optional[str] = None
    default_sending: Optional[str] = None
    line_user_id: Optional[str] = None


class ProfilePictureUpdate(BaseModel):
    image_url: str
