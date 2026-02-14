from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Integer, Identity, String, DateTime
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from ..utils.id_generator import generate_attend_id
from sqlmodel import Relationship

if TYPE_CHECKING:
    from .contact import Contact
    from .user import User

class attend(SQLModel, table=True):
    __tablename__ = "attend"

    # id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY
    id: Optional[int] = Field(
        default=None, 
        sa_column=Column(Integer, Identity(always=True), primary_key=True)
    )

    # attend_id VARCHAR(255) NOT NULL
    attend_id: str = Field(
        default_factory=generate_attend_id,
        sa_column=Column(String(255), nullable=False)
    )
    
    # schedule_id VARCHAR(255) NOT NULL
    # FK to schedule.schedule_id
    schedule_id: str = Field(sa_column=Column(String(255), nullable=False))
    
    # user_id VARCHAR(255) NULL (Nullable for guests)
    # FK to users.user_id if present
    user_id: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    
    # contact_id INTEGER NULL
    # FK to contact.id
    contact_id: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    
    # Guest/Contact Details - REMOVED as per user request
    # name, email, phone, line_id are now fetched via contact_id or user_id
    
    # status VARCHAR(20) DEFAULT 'P'
    status: str = Field(default="P", sa_column=Column(String(20), nullable=True, server_default="P"))
    
    # updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    contact: Optional["Contact"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "attend.contact_id==foreign(Contact.id)",
            "uselist": False
        }
    )
    
    user: Optional["User"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "attend.user_id==foreign(User.user_id)",
            "uselist": False
        }
    )

    def dict(self, *args, **kwargs):
        data = super().dict(*args, **kwargs)
        if self.contact:
            data['nick_name'] = self.contact.nick_name
            data['name'] = self.contact.nick_name
            data['email'] = self.contact.email
            data['phone'] = self.contact.phone
            data['line_id'] = self.contact.line_id
        elif self.user:
            data['nick_name'] = self.user.full_name # Fallback
            data['name'] = self.user.full_name
            data['email'] = self.user.email
            data['phone'] = self.user.phone
            data['line_id'] = self.user.line_id
        return data
