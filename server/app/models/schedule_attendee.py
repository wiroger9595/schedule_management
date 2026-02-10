from sqlmodel import SQLModel, Field
import uuid
from typing import Optional

class ScheduleAttendee(SQLModel, table=True):
    __tablename__ = "schedule_attendee"
    
    schedule_id: uuid.UUID = Field(foreign_key="schedule.id", primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True)
    
    status: str = Field(default="PENDING") # PENDING, ACCEPTED, DECLINED
