from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Integer, Identity, String, DateTime
from typing import Optional
from datetime import datetime
from ..utils.id_generator import generate_contact_id

class Contact(SQLModel, table=True):
    __tablename__ = "contact"

    # id INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY
    id: Optional[int] = Field(
        default=None, 
        sa_column=Column(Integer, Identity(always=True), primary_key=True)
    )
    
    # contract_id VARCHAR(255) NOT NULL
    # User wrote "contract_id", assuming they meant contact record ID.
    contract_id: str = Field(
        default_factory=generate_contact_id,
        sa_column=Column(String(255), nullable=False)
    )
    
    # user_id VARCHAR(255) NOT NULL
    # FK to users.user_id
    user_id: str = Field(sa_column=Column(String(255), nullable=False))
    
    # contact_user_id VARCHAR(255) NOT NULL
    # FK to users.user_id (The friend)
    # contact_user_id VARCHAR(255) NULL
    # FK to users.user_id (The friend) - Optional, as per DDL
    contact_user_id: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))

    # New fields from DDL
    nick_name: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    phone: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    email: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    line_id: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    comment: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    
    # created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=False), nullable=True)
    )
