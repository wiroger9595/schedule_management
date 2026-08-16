from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Integer, Identity, String, DateTime
from typing import Optional, List
from datetime import datetime
from ..utils.id_generator import generate_schedule_id

class Schedule(SQLModel, table=True):
    __tablename__ = "schedule"

    # id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY
    id: Optional[int] = Field(
        default=None, 
        sa_column=Column(Integer, Identity(always=True), primary_key=True)
    )
    
    # user_id VARCHAR(255) NOT NULL
    # This refers to users.user_id, NOT users.id
    user_id: str = Field(sa_column=Column(String(255), nullable=False))
    
    # schedule_id VARCHAR(255) NOT NULL
    schedule_id: str = Field(
        default_factory=generate_schedule_id,
        sa_column=Column(String(255), unique=True, nullable=False)
    )
    
    # meeting_time merged into start_time
    # meeting_end_time merged into end_time
    
    # meeting_start_time TIMESTAMPTZ
    meeting_start_time: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    
    # meeting_end_time TIMESTAMPTZ - Mandatory
    meeting_end_time: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    
    # meeting_location VARCHAR(255) NULL
    # Keeping meeting_location column name for compatibility if needed, or alias?
    # User only asked for start/end time. I will keep meeting_location but alias it to location property?
    # Actually, let's keep meeting_location column but expose 'location' as alias or just use meeting_location
    meeting_location: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    
    # status VARCHAR(2) DEFAULT 'PD' (= Status.PENDING; mobile only recognizes 'PD')
    status: str = Field(default="PD", sa_column=Column(String(2), nullable=True, server_default="PD"))
    
    # cancel_reason VARCHAR(255) NULL
    cancel_reason: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    
    # Contact Details
    contact_id: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    # Legacy fields removed as per refactor plan
    # contact_name, contact_email, contact_phone, contact_line_id are removed.
    
    # created_at TIMESTAMPTZ
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    
    # updated_at TIMESTAMPTZ
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # --- Extra fields for App Functionality (not in requested schema but needed) ---
    
    title: str = Field(default="No Title")
    description: Optional[str] = None
    
    transport_mode: Optional[str] = None
    type: Optional[str] = None # meeting/personal
    attends_display: Optional[str] = Field(default=None, alias="attends") # For text display
    is_reminder: bool = Field(default=False)

    # Departure-reminder support (see ReminderService / background_reminder_scheduler)
    # Computed "time to leave" based on travel duration to meeting_location.
    reminder_leave_by_time: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    # User-adjustable offsets (minutes). Two independent reminders:
    #  - reminder_before_start_minutes: fires N minutes before meeting_start_time
    #  - reminder_before_leave_minutes: fires N minutes before reminder_leave_by_time
    reminder_before_start_minutes: int = Field(
        default=60, sa_column=Column(Integer, nullable=True, server_default="60")
    )
    reminder_before_leave_minutes: int = Field(
        default=60, sa_column=Column(Integer, nullable=True, server_default="60")
    )

    # Coordinates for Map
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)

    # Online event flag
    is_online: bool = Field(default=False)

    # Relationship
    from sqlmodel import Relationship
    # Use string forward reference and explicit join condition since we use custom string IDs
    attend_records: List["attend"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Schedule.schedule_id==foreign(attend.schedule_id)",
            "cascade": "all, delete-orphan",
            "uselist": True
        }
    )

    contact: Optional["Contact"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Schedule.contact_id==foreign(Contact.id)",
            "uselist": False
        }
    )
    
    # Mappings
    @property
    def location(self) -> Optional[str]:
        """Alias for meeting_location for app compatibility"""
        return self.meeting_location
    
    @location.setter
    def location(self, value: Optional[str]):
        self.meeting_location = value
    
    # Override dict() to include computed properties
    def dict(self, *args, **kwargs):
        """Override dict to include @property fields for API serialization"""
        data = super().dict(*args, **kwargs)
        # Add computed properties that the frontend expects
        data['start_time'] = self.meeting_start_time.isoformat() if isinstance(self.meeting_start_time, datetime) else self.meeting_start_time
        data['end_time'] = self.meeting_end_time.isoformat() if isinstance(self.meeting_end_time, datetime) else self.meeting_end_time
        data['location'] = self.meeting_location
        data['latitude'] = self.latitude
        data['longitude'] = self.longitude
        data['id'] = self.schedule_id  # Frontend expects 'id' to be the schedule_id
        data['is_online'] = self.is_online
        
        # Serialize attends
        try:
            data['attends'] = [a.dict() for a in self.attend_records]
        except Exception as e:
            data['attends'] = []
            
        # Serialize contact info from relationship if available
        if self.contact_id and self.contact:
            data['contact_name'] = self.contact.nick_name  # Contact has nick_name
            data['contact_email'] = self.contact.email
            data['contact_phone'] = self.contact.phone
            data['contact_line_id'] = self.contact.line_id
            
        return data
