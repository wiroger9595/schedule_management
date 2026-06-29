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
    is_online: Optional[bool] = None


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
    is_online: Optional[bool] = None


class StatusUpdate(BaseModel):
    status: str
    cancel_reason: Optional[str] = None


class ChatMessage(BaseModel):
    message: str


class ChatRequest(BaseModel):
    message: str
    current_data: Optional[dict] = None
    force_create: bool = False
    confirm_location: bool = False
    confirm_delete: bool = False  # user confirmed delete action
    confirm_past_edit: bool = False  # user confirmed editing a past schedule
    confirm_time_input: bool = False  # user picked a new time via time picker (bypasses AI)
    new_start_time: Optional[str] = None  # ISO datetime from time picker
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    conversation_history: Optional[List[dict]] = None  # [{role, content}, ...]
    schedule_id: Optional[str] = None  # set after schedule created — triggers update instead of create
    schedule_list: Optional[List[dict]] = None  # user's schedules for AI edit/delete context


class InviteItem(BaseModel):
    contact_id: Optional[int] = None
    email: Optional[str] = None
    name: Optional[str] = None


class ScheduleInviteRequest(BaseModel):
    invites: List[InviteItem]


class FeedbackRequest(BaseModel):
    user_message: str
    ai_reply: str
    is_good: bool
    correction: Optional[str] = None
    conversation_json: Optional[str] = None
    model_label: Optional[str] = None


class ChatResponse(BaseModel):
    ai_reply: str
    updated_data: dict
    is_complete: bool
    schedule: Optional[dict] = None
    conflict: Optional[dict] = None
    needs_location_confirm: bool = False
    location_details: Optional[dict] = None
    location_candidates: Optional[List[dict]] = None  # multiple candidates for user to pick
    location_not_found: bool = False          # true when HERE/Nominatim can't find the location
    confirm_delete: Optional[List[dict]] = None  # [{id, title, start_time}, ...] — prompts delete confirmation UI
    schedule_deleted: bool = False  # true after successful delete
    confirm_past_edit: Optional[dict] = None  # {id, title, start_time} — prompts past-schedule edit confirmation UI
    needs_time_input: bool = False  # true when backend needs user to pick a new future time (past-schedule reschedule)
    needs_location_input: bool = False  # true when AI is asking for a location — show location picker instead of text

