from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Integer, Identity, String, DateTime
from typing import Optional
from datetime import datetime
from ..utils.id_generator import generate_attendee_id

class Attendee(SQLModel, table=True):
    __tablename__ = "attendee"

    # id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY
    id: Optional[int] = Field(
        default=None, 
        sa_column=Column(Integer, Identity(always=True), primary_key=True)
    )

    # attend_id VARCHAR(255) NOT NULL
    attend_id: str = Field(
        default_factory=generate_attendee_id,
        sa_column=Column(String(255), nullable=False)
    )
    
    # schedule_id VARCHAR(255) NOT NULL
    # FK to schedule.schedule_id
    schedule_id: str = Field(sa_column=Column(String(255), nullable=False))
    
    # user_id VARCHAR(255) NOT NULL
    # FK to users.user_id
    user_id: str = Field(sa_column=Column(String(255), nullable=False))
    
    # status VARCHAR(20) DEFAULT 'P'
    status: str = Field(default="P", sa_column=Column(String(20), nullable=True, server_default="P"))
    
    # updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
