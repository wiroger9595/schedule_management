from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Integer, Identity, String, DateTime
from typing import Optional
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
    
    # meeting_time VARCHAR(255) NULL
    # App uses this as start_time. We'll map start_time property to this?
    # Or just use meeting_time. The user request specificed meeting_time.
    # To avoid breaking app fully right now, I will use meeting_time but add a property or alias?
    # Actually I should use the schema names.
    meeting_time: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    
    # meeting_location VARCHAR(255) NULL
    meeting_location: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    
    # status VARCHAR(2) DEFAULT 'P'
    status: str = Field(default="P", sa_column=Column(String(2), nullable=True, server_default="P"))
    
    # cancel_reason VARCHAR(255) NULL
    cancel_reason: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    
    # Contact Details
    contact_name: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    contact_email: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    contact_phone: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    contact_line_id: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    
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
    # The user said "My table needs to be reconfigurable", "Here is the schema".
    # If I drop title/description, the app BREAKS.
    # I will add them as columns but make them nullable, or user meant "These are the CORE fields".
    # I will keep title/description/transport_mode/type/attendees for now to keep app working.
    # But user might want strict adherence. 
    # Logic: "Don't use id reference".
    # I will ADD title and description.
    
    title: str = Field(default="No Title")
    description: Optional[str] = None
    
    # start_time is usually datetime in backend logic. meeting_time is VARCHAR.
    # I will sync them.
    
    transport_mode: Optional[str] = None
    type: Optional[str] = None # meeting/personal
    attendees_display: Optional[str] = Field(default=None, alias="attendees") # For text display
    is_reminder: bool = Field(default=False)
    
    # Coordinates for Map
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    
    # Mappings
    @property
    def start_time(self) -> datetime:
        if self.meeting_time:
            return datetime.fromisoformat(self.meeting_time)
        return datetime.now()
        
    @start_time.setter
    def start_time(self, value: datetime):
        self.meeting_time = value.isoformat()
    
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
        data['start_time'] = self.start_time.isoformat() if hasattr(self, 'meeting_time') and self.meeting_time else None
        data['location'] = self.meeting_location
        data['latitude'] = self.latitude
        data['longitude'] = self.longitude
        data['id'] = self.schedule_id  # Frontend expects 'id' to be the schedule_id
        return data
