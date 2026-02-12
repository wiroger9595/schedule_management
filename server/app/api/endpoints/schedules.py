from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List, Optional
from datetime import datetime

from app.models.enums import Status
from ...db.database import get_session
from ...models.schedule import Schedule
from ...models.attend import attend
from ...models.user import User
from ...repositories.schedule_repository import ScheduleRepository
from ...services.gemini_service import gemini_service
from ...services.osmnx_service import OSMnxService
from ...utils.text_validator import validate_schedule_message
from ...schemas.schedule import ScheduleCreate, ScheduleUpdate, StatusUpdate, ChatMessage
from .auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[dict])
@router.get("", response_model=List[dict], include_in_schema=False)
def get_schedules(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = ScheduleRepository(session)
    schedules = repo.get_by_user_id(current_user.user_id)
    # Serialize with computed properties
    results = [s.dict() for s in schedules]
    if results:
        print(f"DEBUG: get_schedules result[0]: {results[0]}")
    return results

@router.post("/", response_model=dict)
@router.post("", response_model=dict, include_in_schema=False)
def create_schedule(data: ScheduleCreate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    # Check if manual creation (title present) or AI creation (message present)
    if data.title and data.title != "No Title":
        # Manual Creation
        print(f"DEBUG: Manual creation with data: {data}")
        start_time_str = data.start_time or data.meeting_time
        start_time = datetime.fromisoformat(start_time_str) if start_time_str else datetime.now()
        
        # Extract contact_id if present
        contact_id = data.contact_id
        if contact_id is not None:
            try:
                contact_id = int(contact_id)
            except (ValueError, TypeError):
                contact_id = None
        
        schedule = Schedule(
            user_id=current_user.user_id,
            title=data.title,
            description=data.description,
            meeting_time=start_time.isoformat(), # Map to meeting_time as per model
            meeting_location=data.location or data.meeting_location,
            transport_mode=data.transport_mode,
            status=Status.PENDING.value,
            latitude=data.latitude,
            longitude=data.longitude,
            
            # Contact Details - Strict contact_id logic
            contact_id=contact_id,
            # Legacy fields removed
        )

        # If contact_id is missing but manual contact details are present, auto-create Contact
        if not contact_id and (data.contact_name or data.contact_phone or data.contact_email or data.contact_line_id):
            print("DEBUG: Auto-creating contact for schedule...")
            from ...models.contact import Contact
            # Create new contact
            new_contact = Contact(
                user_id=current_user.user_id,
                nick_name=data.contact_name or "New Contact", # fallback
                phone=data.contact_phone,
                email=data.contact_email,
                line_id=data.contact_line_id
            )
            session.add(new_contact)
            session.commit()
            session.refresh(new_contact)
            print(f"DEBUG: Auto-created Contact ID: {new_contact.id}")
            schedule.contact_id = new_contact.id
    else:
        # AI Creation
        message = data.message
        if not message:
            raise HTTPException(status_code=400, detail="Message is required for AI creation")
            
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
    
    # Geocoding if needed (Unified logic)
    if schedule.meeting_location and (not schedule.latitude or not schedule.longitude):
        try:
            coords = OSMnxService.get_coordinates(schedule.meeting_location)
            if coords:
                schedule.latitude = coords[0]
                schedule.longitude = coords[1]
        except Exception as e:
            print(f"Geocoding failed: {e}")
            
    # Save via repository
    repo = ScheduleRepository(session)
    created_schedule = repo.create(schedule)
    
    # Process attends
    attends_data = data.attends or []
    if attends_data:
        print(f"DEBUG: Processing {len(attends_data)} attends")
        for att in attends_data:
            # Check if system user or guest
            # System user has 'id' (Contact ID) and 'contact_user_id' (The friend's User ID)
            # Guest has name/email/phone/line_id
            
            # Prioritize contact_user_id from a Contact object
            user_id = att.user_id
            contact_id = att.contact_id
            # If 'id' is integer, it's likely contact_id from selection.
            # But wait, earlier code said 'id' from ContactPicker is int (Contact ID).
            # So we map id -> contact_id.
            
            if isinstance(contact_id, str) and not contact_id.isdigit():
                 contact_id = None # It's a GUID user_id, not contact_id
            elif contact_id is not None:
                 contact_id = int(contact_id)
 
            # Map name: Use name if present, else user_id
            name = att.name or att.user_id
 
            new_attend = attend(
                schedule_id=created_schedule.schedule_id,
                user_id=user_id if user_id else None,
                contact_id=contact_id,
                name=name,
                email=att.email,
                phone=att.phone,
                line_id=att.line_id,
                status=Status.PENDING.value
            )
            session.add(new_attend)
        session.commit()
    
    return created_schedule.dict()

@router.put("/{schedule_id}/status")
@router.patch("/{schedule_id}/status")
def update_schedule_status(schedule_id: str, status_data: StatusUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = ScheduleRepository(session)
    schedule = repo.get_by_schedule_id(schedule_id)
    
    if not schedule or schedule.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Schedule not found")
        
    schedule.status = status_data.status
    if status_data.cancel_reason is not None:
        schedule.cancel_reason = status_data.cancel_reason
    return repo.update(schedule)

@router.put("/{schedule_id}", response_model=dict)
def update_schedule(
    schedule_id: str, 
    data: ScheduleUpdate, 
    current_user: User = Depends(get_current_user), 
    session: Session = Depends(get_session)
):
    repo = ScheduleRepository(session)
    schedule = repo.get_by_schedule_id(schedule_id)
    
    if not schedule or schedule.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Update fields
    if data.title is not None: schedule.title = data.title
    if data.description is not None: schedule.description = data.description
    if data.start_time is not None: schedule.start_time = datetime.fromisoformat(data.start_time)
    if data.meeting_time is not None: schedule.start_time = datetime.fromisoformat(data.meeting_time)
    
    if data.transport_mode is not None: schedule.transport_mode = data.transport_mode
    
    # Update contact_id if present
    if data.contact_id is not None:
        schedule.contact_id = int(data.contact_id)
    
    # If contact_id NOT in data (or explicitly None/removed?) but manual details provided?
    # Usually update sends what's changed.
    # If user edits "Contact Name" text field manually without picking a contact, we should create one.
    # But usually UI should handle "Add to Contacts".
    # Assuming strict logic: If data has contact_name etc, we create a contract.
    
    if data.contact_name or data.contact_phone or data.contact_email or data.contact_line_id:
         print("DEBUG: Auto-creating contact for schedule update...")
         from ...models.contact import Contact
         new_contact = Contact(
            user_id=current_user.user_id,
            nick_name=data.contact_name or "New Contact",
            phone=data.contact_phone,
            email=data.contact_email,
            line_id=data.contact_line_id
         )
         session.add(new_contact)
         session.commit()
         session.refresh(new_contact)
         schedule.contact_id = new_contact.id
         print(f"DEBUG: Auto-created Contact ID: {new_contact.id} and linked to schedule")
    
    print(f"DEBUG: update_schedule received data: {data}")
    # If lat/lon explicit, use them (Manual Pick)
    if data.latitude is not None and data.longitude is not None:
        print(f"DEBUG: setting manual lat/lon: {data.latitude}, {data.longitude}")
        schedule.latitude = data.latitude
        schedule.longitude = data.longitude
        if data.location is not None:
            schedule.location = data.location
    
    # If only location string changed (Text Edit), try geocode
    elif data.location is not None and data.location != schedule.location:
        schedule.location = data.location
        try:
            coords = OSMnxService.get_coordinates(schedule.location)
            if coords:
                schedule.latitude = coords[0]
                schedule.longitude = coords[1]
        except:
            pass # Keep old coords or none if geocode fails
            
            
    updated_schedule = repo.update(schedule)
    
    # Update attends if provided
    if data.attends is not None:
        attends_data = data.attends
        # Delete existing attends
        # This requires a method in repo or direct session deletion
        from sqlmodel import delete
        from ...models.attend import attend
        session.exec(delete(attend).where(attend.schedule_id == schedule_id))
        
        # Add new ones
        for att in attends_data:
            # Prioritize contact_user_id from a Contact object
            user_id = att.user_id
            contact_id = att.contact_id
            
            if isinstance(contact_id, str) and not contact_id.isdigit():
                 contact_id = None 
            elif contact_id is not None:
                 contact_id = int(contact_id)
            
            # Map name
            name = att.name or att.user_id

            new_attend = attend(
                schedule_id=schedule_id,
                user_id=user_id if user_id else None,
                contact_id=contact_id,
                name=name,
                email=att.email,
                phone=att.phone,
                line_id=att.line_id,
                status="P"
            )
            session.add(new_attend)
        session.commit()
    
    updated_schedule = repo.get_by_schedule_id(schedule_id) # Refresh to get latest state if needed
    result = updated_schedule.dict()
    print(f"DEBUG: update_schedule returning: {result}")
    return result

@router.post("/chat")
def chat_schedule(
    message_data: ChatMessage,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    user_message = message_data.message.strip()
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
            status=Status.PENDING.value,
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
