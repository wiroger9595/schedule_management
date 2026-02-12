from pydantic import BaseModel
from typing import Optional


class ContactCreate(BaseModel):
    nick_name: Optional[str] = None
    name: Optional[str] = None  # alias for nick_name
    phone: Optional[str] = None
    email: Optional[str] = None
    line_id: Optional[str] = None
    contact_user_id: Optional[str] = None
    comment: Optional[str] = None


class ContactUpdate(BaseModel):
    nick_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    line_id: Optional[str] = None
    comment: Optional[str] = None
    contact_user_id: Optional[str] = None
