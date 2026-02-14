from pydantic import BaseModel
from typing import Optional, List


class AttendCreate(BaseModel):
    user_id: Optional[str] = None
    contact_id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    line_id: Optional[str] = None


class ScheduleCreate(BaseModel):
    title: Optional[str] = "No Title"
    description: Optional[str] = None
    meeting_time: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    meeting_location: Optional[str] = None
    location: Optional[str] = None
    transport_mode: Optional[str] = None
    type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_id: Optional[int] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_line_id: Optional[str] = None
    attends: Optional[List[AttendCreate]] = None
    message: Optional[str] = None


class ScheduleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    meeting_time: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    meeting_location: Optional[str] = None
    location: Optional[str] = None
    transport_mode: Optional[str] = None
    type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_id: Optional[int] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_line_id: Optional[str] = None
    contact_line_id: Optional[str] = None
    attends: Optional[List[AttendCreate]] = None
    status: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str
    cancel_reason: Optional[str] = None


class ChatMessage(BaseModel):
    message: str


class ChatRequest(BaseModel):
    message: str
    current_data: Optional[dict] = None


class ChatResponse(BaseModel):
    ai_reply: str
    updated_data: dict
    is_complete: bool
    schedule: Optional[dict] = None

