from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ContactCreate(BaseModel):
    nick_name: Optional[str] = None
    name: Optional[str] = None  # alias for nick_name
    phone: Optional[str] = None
    email: Optional[str] = None
    line_id: Optional[str] = None
    contact_user_id: Optional[str] = None
    comment: Optional[str] = None
    default_notification_method: Optional[str] = "mobile"


class ContactUpdate(BaseModel):
    nick_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    line_id: Optional[str] = None
    comment: Optional[str] = None
    contact_user_id: Optional[str] = None
    default_notification_method: Optional[str] = None


class ContactRead(ContactCreate):
    id: int
    user_id: str
    created_at: Optional[datetime] = None
    profile_image_path: Optional[str] = None
    default_notification_method: Optional[str] = "mobile"

    class Config:
        from_attributes = True

class ContactValidateRequest(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    line_id: Optional[str] = None
    exclude_contact_id: Optional[int] = None

class ContactValidateResponse(BaseModel):
    is_valid: bool
    duplicate_field: Optional[str] = None
