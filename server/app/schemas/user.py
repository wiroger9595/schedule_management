from pydantic import BaseModel
from typing import Optional


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
