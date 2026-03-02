from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CommentBase(BaseModel):
    comment_description: str
    status: Optional[str] = "P"

class CommentCreate(CommentBase):
    pass

class CommentUpdate(BaseModel):
    comment_description: Optional[str] = None
    status: Optional[str] = None

class CommentRead(CommentBase):
    id: int
    comment_id: str
    user_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
