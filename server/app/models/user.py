from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Integer, Identity, String, DateTime
from typing import Optional
from datetime import datetime
from ..utils.id_generator import generate_user_id

class User(SQLModel, table=True):
    __tablename__ = "users" # Changed from "user" to match request "users" (plural)

    # id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY
    id: Optional[int] = Field(
        default=None, 
        sa_column=Column(Integer, Identity(always=True), primary_key=True)
    )
    
    # user_id VARCHAR(255) NOT NULL
    user_id: str = Field(
        default_factory=generate_user_id, 
        sa_column=Column(String(255), unique=True, nullable=False)
    )
    
    # email VARCHAR(255) NULL
    email: Optional[str] = Field(
        default=None, 
        sa_column=Column(String(255), nullable=True, unique=True) # Keeping unique for logic
    )
    
    hashed_password: Optional[str] = Field(default=None) # Start keeping this? Request didn't specify but we need it for auth
    
    full_name: Optional[str] = Field(default=None) # Needed for app logic
    
    # phone VARCHAR(255) NULL
    phone: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    
    # line_id VARCHAR(255) NULL
    line_id: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    
    # profile_image_path VARCHAR(255)
    profile_image_path: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    
    # public_id VARCHAR(255) NULL
    public_id: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True))
    
    # status VARCHAR(2) DEFAULT 'Y'
    status: str = Field(default="Y", sa_column=Column(String(2), nullable=True, server_default="Y"))
    
    # created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), nullable=True) # user asked for TIMESTAMPTZ
    )
    
    # updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    
    # Compat: Add 'profile_picture' property to map to 'profile_image_path' if needed by pydantic, 
    # but strictly we should use 'profile_image_path'
    
    # Auth fields that were not in schema but required for app
    google_id: Optional[str] = None
    apple_id: Optional[str] = None
