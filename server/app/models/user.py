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
    
    # language VARCHAR(10) NULL
    language: Optional[str] = Field(default="zh-TW", sa_column=Column(String(10), nullable=True))
    
    # status VARCHAR(2) DEFAULT 'Y'
    status: str = Field(default="Y", sa_column=Column(String(2), nullable=True, server_default="Y"))

    # default_sending VARCHAR(20) DEFAULT 'line'
    default_sending: Optional[str] = Field(default="line", sa_column=Column(String(20), nullable=True, server_default="line"))
    
    # line_user_id VARCHAR(255) NULL (Unique ID from Line Platform)
    line_user_id: Optional[str] = Field(default=None, sa_column=Column(String(255), nullable=True, unique=True))

    # fcm_token — Firebase Cloud Messaging device token for push notifications
    fcm_token: Optional[str] = Field(default=None, sa_column=Column(String(512), nullable=True))

    # ── 訂閱方案（RevenueCat webhook 維護）───────────────────────────────────
    # plan: 'free' = 每月限額走我們的 key；'pro' = 用戶自帶 key，不計次
    plan: str = Field(default="free", sa_column=Column(String(20), nullable=True, server_default="free"))

    # 訂閱到期時間；過期後 chat 端點會當成 free 處理（不主動改 plan，等 webhook）
    plan_expires_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # ── 用戶自帶 AI（BYOK，任意 OpenAI 相容端點）─────────────────────────────
    ai_base_url: Optional[str] = Field(default=None, sa_column=Column(String(500), nullable=True))
    ai_model: Optional[str] = Field(default=None, sa_column=Column(String(200), nullable=True))
    # Fernet 密文，永遠不回明文給前端（見 core/crypto.py）
    ai_api_key_enc: Optional[str] = Field(default=None, sa_column=Column(String(1000), nullable=True))

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
