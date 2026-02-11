from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List, Optional
from ...db.database import get_session
from ...models.schedule import Schedule
from ...models.user import User
from ...repositories.schedule_repository import ScheduleRepository
from ...services.gemini_service import gemini_service
from ...services.osmnx_service import OSMnxService
from ...utils.text_validator import validate_schedule_message
from .auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[dict])
def get_schedules(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = ScheduleRepository(session)
    schedules = repo.get_by_user_id(current_user.user_id)
    # Serialize with computed properties
    results = [s.dict() for s in schedules]
    if results:
        print(f"DEBUG: get_schedules result[0]: {results[0]}")
    return results

@router.post("/", response_model=dict)
def create_schedule(data: dict, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    message = data.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
        
    # Text validation
    if not validate_schedule_message(message):
        raise HTTPException(status_code=400, detail="Invalid input content")
        
    # Gemini processing
    try:
        schedule_data = gemini_service.extract_schedule_from_text(message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")
        
    # Create Schedule object
    schedule = Schedule(
        user_id=current_user.user_id,
        title=schedule_data.get("title", "未命名行程"),
        start_time=schedule_data.get("start_time"),
        end_time=schedule_data.get("end_time"),
        location=schedule_data.get("location"),
        description=schedule_data.get("description"),
        is_all_day=schedule_data.get("is_all_day", False)
    )
    
    # Geocoding
    if schedule.location:
        try:
            coords = OSMnxService.get_coordinates(schedule.location)
            if coords:
                schedule.latitude = coords[0]
                schedule.longitude = coords[1]
        except Exception as e:
            print(f"Geocoding failed: {e}")
            
    # Save via repository
    repo = ScheduleRepository(session)
    created_schedule = repo.create(schedule)
    return created_schedule.dict()

@router.put("/{schedule_id}/status")
def update_schedule_status(schedule_id: str, status_data: dict, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = ScheduleRepository(session)
    schedule = repo.get_by_schedule_id(schedule_id)
    
    if not schedule or schedule.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Schedule not found")
        
    schedule.status = status_data.get("status", schedule.status)
    schedule.status = status_data.get("status", schedule.status)
    return repo.update(schedule)

@router.put("/{schedule_id}", response_model=dict)
def update_schedule(
    schedule_id: str, 
    data: dict, 
    current_user: User = Depends(get_current_user), 
    session: Session = Depends(get_session)
):
    repo = ScheduleRepository(session)
    schedule = repo.get_by_schedule_id(schedule_id)
    
    if not schedule or schedule.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Update fields
    if "title" in data: schedule.title = data["title"]
    if "description" in data: schedule.description = data["description"]
    from datetime import datetime
    if "startTime" in data: schedule.start_time = datetime.fromisoformat(data["startTime"])
    if "start_time" in data: schedule.start_time = datetime.fromisoformat(data["start_time"])
    
    if "transportMode" in data: schedule.transport_mode = data["transportMode"]
    if "transport_mode" in data: schedule.transport_mode = data["transport_mode"]
    
    print(f"DEBUG: update_schedule received data: {data}")
    # If lat/lon explicit, use them (Manual Pick)
    if "latitude" in data and "longitude" in data:
        print(f"DEBUG: setting manual lat/lon: {data['latitude']}, {data['longitude']}")
        schedule.latitude = data["latitude"]
        schedule.longitude = data["longitude"]
        if "location" in data:
            schedule.location = data["location"]
    
    # If only location string changed (Text Edit), try geocode
    elif "location" in data and data["location"] != schedule.location:
        schedule.location = data["location"]
        try:
            coords = OSMnxService.get_coordinates(schedule.location)
            if coords:
                schedule.latitude = coords[0]
                schedule.longitude = coords[1]
        except:
            pass # Keep old coords or none if geocode fails
            
    updated_schedule = repo.update(schedule)
    result = updated_schedule.dict()
    print(f"DEBUG: update_schedule returning: {result}")
    return result

@router.post("/chat")
def chat_schedule(
    message_data: dict,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    from datetime import datetime
    
    user_message = message_data.get("message", "").strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="訊息不能為空")
    
    try:
        if not validate_schedule_message(user_message):
            return {
                "ai_response": "請問具體的時間是什麼時候呢？（例如：明天下午3點、下週一早上10點）",
                "schedule": None
            }

        schedule_info = gemini_service.extract_schedule_info(user_message)
        
        if not schedule_info.get("title") or not schedule_info.get("start_time"):
            raise HTTPException(status_code=400, detail="請提供更詳細的資訊（至少需要標題和時間）")
        
        start_dt = datetime.fromisoformat(schedule_info["start_time"])
        
        schedule = Schedule(
            user_id=current_user.user_id,
            title=schedule_info["title"],
            description=schedule_info.get("description"),
            meeting_time=start_dt.isoformat(),
            meeting_location=schedule_info.get("location"),
            transport_mode=schedule_info.get("transport_mode"),  
            status="PENDING",
            type="personal"
        )
        
        # Geocoding logic via Service? or Repo?
        # Ideally Service. But we have it inline in main.py.
        # Let's keep inline here or replicate logic from create_schedule
        if schedule.meeting_location:
             coords = OSMnxService.get_coordinates(schedule.meeting_location)
             if coords:
                 schedule.latitude = coords[0]
                 schedule.longitude = coords[1]
        
        repo = ScheduleRepository(session)
        repo.create(schedule)
        
        ai_response = gemini_service.generate_confirmation_message(schedule_info)
        
        return {
            "ai_response": ai_response,
            "schedule": schedule.dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error in chat_schedule: {e}")
        raise HTTPException(status_code=500, detail="處理失敗，請稍後再試")
