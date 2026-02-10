from fastapi import File, UploadFile, FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select, SQLModel
from typing import List, Optional
from .models.schedule import Schedule
from .models.user import User
from .services.osmnx_service import OSMnxService
from .services.tdx_service import TDXService
from .core.auth import get_password_hash, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from .core.redis_client import redis_client
from .services.gemini_service import gemini_service
from .utils.text_validator import validate_schedule_message
from jose import jwt, JWTError
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Schedule Management API")



security = HTTPBearer()

# Database Settings (PostgreSQL)
postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "schedule_management")

DATABASE_URL = f"postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

from sqlmodel import create_engine
engine = create_engine(DATABASE_URL)

def get_session():
    with Session(engine) as session:
        yield session

@app.on_event("startup")
def on_startup():
    from sqlmodel import SQLModel
    # Import models so metadata is populated
    from .models.user import User
    from .models.schedule import Schedule
    from .models.contact import Contact
    from .models.attendee import Attendee
    
    SQLModel.metadata.create_all(engine)


def get_current_user(auth: HTTPAuthorizationCredentials = Security(security), session: Session = Depends(get_session)):
    try:
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Check if token exists in Redis
        if not redis_client.validate_token(user_id, auth.credentials):
            raise HTTPException(status_code=401, detail="Token has been revoked")
        
        user = session.exec(select(User).where(User.user_id == user_id)).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# --- Auth Routes ---

@app.post("/api/auth/register")
def register(user_data: dict, session: Session = Depends(get_session)):

    
    # Validate required fields
    email = user_data.get('email')
    password = user_data.get('password')
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    
    # Check if email already exists
    existing_user = session.exec(select(User).where(User.email == email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    

    
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        full_name=user_data.get('full_name')
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return {
        "message": "User created successfully"
    }

@app.post("/api/auth/login")
def login(login_data: dict, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == login_data['email'])).first()
    if not user or not verify_password(login_data['password'], user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.user_id})
    # Store token in Redis
    redis_client.set_token(user.user_id, access_token)
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "user": {
            "email": user.email, 
            "full_name": user.full_name,
            "account_number": user.user_id, # Frontend expects account_number
            "profile_picture": user.profile_image_path, # Frontend expects profile_picture
            "phone": user.phone,
            "line_id": user.line_id,
            "language": "zh-TW" # Default or from DB if added
        }
    }

@app.post("/api/auth/google")
def google_auth(data: dict, session: Session = Depends(get_session)):
    # In a real app, verify the google id_token here.
    # For now, we mock the verification and assume 'data' has sub, email, name
    google_id = data.get("sub")
    email = data.get("email")
    
    user = session.exec(select(User).where(User.google_id == google_id)).first()
    if not user:
        # Check if email exists
        user = session.exec(select(User).where(User.email == email)).first()
        if user:
            user.google_id = google_id
        else:
            user = User(email=email, google_id=google_id, full_name=data.get("name"))
        session.add(user)
        session.commit()
        session.refresh(user)
    
    access_token = create_access_token(data={"sub": user.user_id})
    # Store token in Redis
    redis_client.set_token(user.user_id, access_token)
    return {"access_token": access_token}

@app.post("/api/auth/apple")
def apple_auth(data: dict, session: Session = Depends(get_session)):
    # Mock apple verification
    apple_id = data.get("sub")
    email = data.get("email")
    
    user = session.exec(select(User).where(User.apple_id == apple_id)).first()
    if not user:
        user = session.exec(select(User).where(User.email == email)).first()
        if user:
            user.apple_id = apple_id
        else:
            user = User(email=email, apple_id=apple_id, full_name=data.get("name"))
        session.add(user)
        session.commit()
        session.refresh(user)
    
    access_token = create_access_token(data={"sub": user.user_id})
    # Store token in Redis
    redis_client.set_token(user.user_id, access_token)
    return {"access_token": access_token}


@app.post("/api/auth/logout")
def logout(
    auth: HTTPAuthorizationCredentials = Security(security),
    current_user: User = Depends(get_current_user)
):
    """登出端點：刪除 Redis 中的 Token"""
    redis_client.delete_token(current_user.user_id, auth.credentials)
    return {"message": "Logged out successfully"}


@app.post("/api/chat/schedule")
def chat_schedule(
    message_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    AI 對話式行程建立
    
    Request body:
    {
        "message": "明天下午3點去台北101開會"
    }
    
    Response:
    {
        "ai_response": "✅ 已為您建立行程...",
        "schedule": { ... }
    }
    """
    user_message = message_data.get("message", "").strip()
    
    if not user_message:
        raise HTTPException(status_code=400, detail="訊息不能為空")
    
    try:
        # 1. 啟發式驗證：檢查訊息是否包含基本行程關鍵字
        if not validate_schedule_message(user_message):
            # 如果關鍵字不足，直接回傳提示，不消耗 API 額度
            return {
                "ai_response": "請問具體的時間是什麼時候呢？（例如：明天下午3點、下週一早上10點）",
                "schedule": None
            }

        # 2. 使用 Gemini 提取行程資訊
        schedule_info = gemini_service.extract_schedule_info(user_message)
        
        # 驗證必要欄位
        if not schedule_info.get("title") or not schedule_info.get("start_time"):
            raise HTTPException(
                status_code=400, 
                detail="請提供更詳細的資訊（至少需要標題和時間）"
            )
        
        # 建立 Schedule 物件
        # Note: SQLModel constructor doesn't use property setters, so we must set meeting_time directly
        start_dt = datetime.fromisoformat(schedule_info["start_time"])
        schedule = Schedule(
            user_id=current_user.user_id,
            title=schedule_info["title"],
            description=schedule_info.get("description"),
            meeting_time=start_dt.isoformat(), # Explicitly set column field
            meeting_location=schedule_info.get("location"), # Use correct column name
            transport_mode=schedule_info.get("transport_mode"),  
            status="PENDING",
            type="personal" # Default type
        )
        
        session.add(schedule)
        session.commit()
        session.refresh(schedule)
        
        # 生成確認訊息
        ai_response = gemini_service.generate_confirmation_message(schedule_info)
        
        return {
            "ai_response": ai_response,
            "schedule": schedule
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error in chat_schedule: {e}")
        raise HTTPException(status_code=500, detail="處理失敗，請稍後再試")


# --- User Profile Endpoints ---

@app.get("/api/users/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """取得當前用戶資訊"""
    return {
        **current_user.dict(),
        "account_number": current_user.user_id,
        "profile_picture": current_user.profile_image_path
    }

@app.patch("/api/users/profile")
def update_profile(
    profile_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """更新用戶資料"""
    if 'full_name' in profile_data:
        current_user.full_name = profile_data['full_name']
    if 'user_id' in profile_data:
        # Check if new user_id is already taken (if changed)
        if profile_data['user_id'] != current_user.user_id:
            existing = session.exec(select(User).where(User.user_id == profile_data['user_id'])).first()
            if existing:
                raise HTTPException(status_code=400, detail="User ID already exists")
        current_user.user_id = profile_data['user_id']
        
    if 'profile_picture' in profile_data:
        current_user.profile_image_path = profile_data['profile_picture']
        
    if 'phone' in profile_data:
        current_user.phone = profile_data['phone']
        
    if 'line_id' in profile_data:
        current_user.line_id = profile_data['line_id']
    
    # Update timestamp
    current_user.updated_at = datetime.now()
    
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return {
        **current_user.dict(),
        "account_number": current_user.user_id,
        "profile_picture": current_user.profile_image_path
    }

@app.post("/api/users/upload-photo")
async def upload_photo(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """上傳用戶頭像到 Cloudinary"""
    from .services.cloudinary_service import upload_user_photo
    
    # 驗證檔案類型
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="只支援 JPG/PNG 格式")
    
    # 讀取檔案
    file_data = await file.read()
    
    # 上傳到 Cloudinary
    # 上傳到 Cloudinary
    try:
        # Delete old photo if exists
        if current_user.public_id:
            from .services.cloudinary_service import delete_user_photo
            
            old_id = current_user.public_id
            
            # Simple heuristic: if ID contains "/", treat as full path (old format)
            # If not, construct full path (new format: user-photo/{user_id}/{filename})
            if "/" not in old_id:
                old_id = f"user-photo/{current_user.user_id}/{old_id}"
                
            delete_user_photo(old_id)

        result = upload_user_photo(
            str(current_user.user_id),
            file_data,
            file.filename
        )
        
        # 更新用戶資料
        current_user.profile_image_path = result['url']
        # Store JUST the filename part as public_id (as requested)
        current_user.public_id = result['filename']
        
        current_user.updated_at = datetime.now()
        session.add(current_user)
        session.commit()
        session.refresh(current_user)
        
        print(f"DEBUG: Photo uploaded for user {current_user.user_id}")
        print(f"DEBUG: Cloudinary URL: {result['url']}")
        print(f"DEBUG: Cloudinary Public ID: {result['public_id']}")
        
        return {"photo_url": result['url'], "message": "頭像上傳成功"}
    except Exception as e:
        print(f"Error uploading photo: {e}")
        raise HTTPException(status_code=500, detail=f"上傳失敗：{str(e)}")

# --- Contact System ---

@app.get("/api/contacts")
def get_contacts(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    from .models.contact import Contact
    
    # Simple query: select * from contact where owner_id = current_user.user_id
    contacts = session.exec(select(Contact).where(Contact.owner_id == current_user.user_id)).all()
    
    # Enrich with user details
    result = []
    for c in contacts:
        # Use exec/select because find by user_id string
        friend = session.exec(select(User).where(User.user_id == c.contact_user_id)).first()
        if friend:
            result.append({
                "id": str(c.contact_user_id), # Return friend's user ID as the main identifier
                "contact_id_record": str(c.id), # Internal record ID
                "email": friend.email,
                "full_name": friend.full_name,
                "profile_picture": friend.profile_image_path # Map back
            })
    return result

@app.post("/api/contacts")
def add_contact(
    data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    from .models.contact import Contact
    
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
        
    # Find user by email
    friend = session.exec(select(User).where(User.email == email)).first()
    if not friend:
        raise HTTPException(status_code=404, detail="User not found")
        
    if friend.id == current_user.id: # Valid comparison because both are mapped ORM objects
        raise HTTPException(status_code=400, detail="Cannot add yourself")
        
    # Check if already added
    exists = session.exec(select(Contact).where(
        Contact.owner_id == current_user.user_id,
        Contact.contact_user_id == friend.user_id
    )).first()
    
    if exists:
        raise HTTPException(status_code=400, detail="User already in contacts")
        
    # Create contact
    contact = Contact(owner_id=current_user.user_id, contact_user_id=friend.user_id)
    session.add(contact)
    session.commit()
    
    return {"message": "Contact added", "friend": {"id": str(friend.id), "full_name": friend.full_name}}

@app.delete("/api/contacts/{friend_id}")
def delete_contact(
    friend_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    from .models.contact import Contact
    
    # friend_id is string (e.g. ur...)
    if not friend_id:
        raise HTTPException(status_code=400, detail="Invalid friend ID")

    contact = session.exec(select(Contact).where(
        Contact.owner_id == current_user.user_id,
        Contact.contact_user_id == friend_id
    )).first()
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
        
    session.delete(contact)
    session.commit()
    
    return {"message": "Contact removed"}





# Services
tdx_service = TDXService(
    client_id=os.getenv("TDX_CLIENT_ID", ""),
    client_secret=os.getenv("TDX_CLIENT_SECRET", "")
)

@app.get("/api/schedules", response_model=List[Schedule])
def read_schedules(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    return session.exec(select(Schedule).where(Schedule.user_id == current_user.user_id)).all()


class ScheduleCreate(SQLModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    location: Optional[str] = None
    transport_mode: Optional[str] = None

    attendee_ids: List[str] = []

@app.post("/api/schedules", response_model=Schedule)
def create_schedule(
    schedule_data: ScheduleCreate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    # Create Schedule object
    schedule = Schedule(
        user_id=current_user.user_id,
        title=schedule_data.title,
        description=schedule_data.description,
        meeting_time=schedule_data.start_time.isoformat(), # Set DB column
        meeting_location=schedule_data.location, # Set DB column
        transport_mode=schedule_data.transport_mode,
        status="PENDING"
    )
    
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    
    # Process attendees
    if schedule_data.attendee_ids:
        from app.models.attendee import Attendee
        # Update names in schedule.attendees for display (optional, but good for simple UI)
        attendee_names = []
        
        for uid in schedule_data.attendee_ids:
            try:
                # Add link (Attendee uses string IDs)
                link = Attendee(schedule_id=schedule.schedule_id, user_id=str(uid))
                session.add(link)
                
                # Get name for text record
                friend = session.exec(select(User).where(User.user_id == str(uid))).first()
                if friend and friend.full_name:
                    attendee_names.append(friend.full_name)
                    
            except Exception as e:
                print(f"Error adding attendee {uid}: {e}")
        
        # Update schedule text attendees field
        if attendee_names:
            schedule.attendees = ", ".join(attendee_names)
            schedule.type = "meeting" # Auto-set type to meeting
            session.add(schedule)
            session.commit()
            session.refresh(schedule)
            
    return schedule
@app.get("/api/estimate")
def estimate_travel(lat1: float, lon1: float, lat2: float, lon2: float, mode: str = "car"):
    if mode == "transit":
        res = tdx_service.get_transit_route(lat1, lon1, lat2, lon2)
    else:
        res = OSMnxService.get_travel_estimate(lat1, lon1, lat2, lon2, mode)
    
    if not res:
        raise HTTPException(status_code=400, detail="Travel estimation failed")
    return res

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
