from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List, Optional
from datetime import datetime
import arrow

from app.models.enums import Status
from ...db.database import get_session
from ...models.schedule import Schedule
from ...models.attend import attend
from ...models.user import User
from ...repositories.schedule_repository import ScheduleRepository
from ...services.ai_service import ai_service
from ...services.here_service import HereService
from ...services.notification_service import notification_service
from ...utils.text_validator import validate_schedule_message
from ...schemas.schedule import ScheduleCreate, ScheduleUpdate, StatusUpdate, ChatMessage, ChatRequest, ChatResponse
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
        
        end_time_str = data.end_time
        meeting_end_time = datetime.fromisoformat(end_time_str) if end_time_str else None
        
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
            meeting_start_time=start_time,
            meeting_end_time=meeting_end_time,
            # meeting_time removed
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
            print("DEBUG: Auto-creating or linking contact for schedule...")
            from ...models.contact import Contact
            from sqlmodel import select
            
            existing_contact = None
            if data.contact_phone: existing_contact = session.exec(select(Contact).where(Contact.user_id == current_user.user_id, Contact.phone == data.contact_phone)).first()
            if not existing_contact and data.contact_email: existing_contact = session.exec(select(Contact).where(Contact.user_id == current_user.user_id, Contact.email == data.contact_email)).first()
            if not existing_contact and data.contact_line_id: existing_contact = session.exec(select(Contact).where(Contact.user_id == current_user.user_id, Contact.line_id == data.contact_line_id)).first()

            if existing_contact:
                schedule.contact_id = existing_contact.id
                print(f"DEBUG: Linked to existing Contact ID: {existing_contact.id}")
            else:
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
            
        # AI processing
        try:
            schedule_data = ai_service.extract_schedule_info(message)
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
            coords = HereService.get_coordinates(schedule.meeting_location)
            if coords:
                schedule.latitude = coords[0]
                schedule.longitude = coords[1]
        except Exception as e:
            print(f"Geocoding failed: {e}")
            
    # Save via repository
    repo = ScheduleRepository(session)
    
    # Conflict check specifically for manual creations. AI check is already handled.
    if data.title and data.title != "No Title":
         conflicts = repo.find_overlapping(
             user_id=current_user.user_id,
             start_time=schedule.meeting_start_time,
             end_time=schedule.meeting_end_time
         )
         if conflicts:
             raise HTTPException(status_code=409, detail="該時間已經有計劃了，請修改時間")

    created_schedule = repo.create(schedule)
    
    # Process attends
    attends_data = data.attends or []
    if attends_data:
        print(f"DEBUG: Processing {len(attends_data)} attends")
        
        # 1. Collect contact_ids to batch fetch linked user_ids
        contact_ids_to_fetch = []
        for att in attends_data:
            contact_id = att.contact_id
            # Normalize contact_id
            if isinstance(contact_id, str) and not contact_id.isdigit():
                 pass 
            elif contact_id is not None:
                 contact_ids_to_fetch.append(int(contact_id))
        
        # 2. Fetch Contacts map
        contact_user_map = {}
        contact_models_map = {}
        if contact_ids_to_fetch:
            from ...models.contact import Contact
            from sqlmodel import select
            statement = select(Contact).where(Contact.id.in_(contact_ids_to_fetch))
            contacts = session.exec(statement).all()
            for c in contacts:
                contact_models_map[c.id] = c
                if c.contact_user_id:
                    contact_user_map[c.id] = c.contact_user_id
        
        for att in attends_data:
            # Check if system user or guest
            # System user has 'id' (Contact ID) and 'contact_user_id' (The friend's User ID)
            # Guest has name/email/phone/line_id
            
            # Prioritize contact_user_id from a Contact object
            user_id = att.user_id
            contact_id = att.contact_id

            if isinstance(contact_id, str) and not contact_id.isdigit():
                 contact_id = None # It's a GUID user_id, not contact_id
            elif contact_id is not None:
                 contact_id = int(contact_id)
            
            # If user_id is missing, try to get from contact map
            if not user_id and contact_id and contact_id in contact_user_map:
                user_id = contact_user_map[contact_id]

            new_attend = attend(
                schedule_id=created_schedule.schedule_id,
                user_id=user_id if user_id else None,
                contact_id=contact_id,
                status=Status.PENDING.value
            )
            session.add(new_attend)
        session.commit()
        
        # Dispatch notifications
        created_attends = session.exec(select(attend).where(attend.schedule_id == created_schedule.schedule_id)).all()
        notification_service.notify_attendees(created_schedule.title, created_attends, contact_models_map)
    
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

    print(f"DEBUG: update_schedule received data: {data.dict(exclude_unset=True)}")
    
    # Update fields
    if data.title is not None: schedule.title = data.title
    if data.description is not None: schedule.description = data.description
    if data.start_time is not None: 
        print(f"DEBUG: Updating start_time to {data.start_time}")
        schedule.meeting_start_time = datetime.fromisoformat(data.start_time)
    if data.meeting_time is not None: schedule.meeting_start_time = datetime.fromisoformat(data.meeting_time) # Legacy support
    if data.end_time is not None: 
        print(f"DEBUG: Updating end_time to {data.end_time}")
        schedule.meeting_end_time = datetime.fromisoformat(data.end_time)
    else:
        print("DEBUG: end_time is None in update data")
        
    # Check for conflicts after updating times
    if data.start_time is not None or data.end_time is not None:
         conflicts = repo.find_overlapping(
             user_id=current_user.user_id,
             start_time=schedule.meeting_start_time,
             end_time=schedule.meeting_end_time,
             exclude_schedule_id=schedule.schedule_id
         )
         if conflicts:
             raise HTTPException(status_code=409, detail="該時間已經有計劃了，請修改時間")
    

    
    if data.transport_mode is not None: schedule.transport_mode = data.transport_mode
    if data.status is not None: schedule.status = data.status
    
    # Update contact_id if present
    if data.contact_id is not None:
        schedule.contact_id = int(data.contact_id)
    
    # If contact_id NOT in data (or explicitly None/removed?) but manual details provided?
    # Usually update sends what's changed.
    # If user edits "Contact Name" text field manually without picking a contact, we should create one.
    # But usually UI should handle "Add to Contacts".
    # Assuming strict logic: If data has contact_name etc, we create or link a contract.
    
    if data.contact_id is None and (data.contact_name or data.contact_phone or data.contact_email or data.contact_line_id):
         print("DEBUG: Auto-creating/linking contact for schedule update...")
         from ...models.contact import Contact
         from sqlmodel import select
         
         existing_contact = None
         if data.contact_phone: existing_contact = session.exec(select(Contact).where(Contact.user_id == current_user.user_id, Contact.phone == data.contact_phone)).first()
         if not existing_contact and data.contact_email: existing_contact = session.exec(select(Contact).where(Contact.user_id == current_user.user_id, Contact.email == data.contact_email)).first()
         if not existing_contact and data.contact_line_id: existing_contact = session.exec(select(Contact).where(Contact.user_id == current_user.user_id, Contact.line_id == data.contact_line_id)).first()

         if existing_contact:
             schedule.contact_id = existing_contact.id
             print(f"DEBUG: Linked to existing Contact ID: {existing_contact.id} during update")
         else:
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
            schedule.meeting_location = data.location
            schedule.location = data.location
    
    # If only location string changed (Text Edit), try geocode
    elif data.location is not None and data.location != schedule.meeting_location:
        schedule.meeting_location = data.location
        schedule.location = data.location
        try:
            coords = HereService.get_coordinates(schedule.meeting_location)
            if coords:
                schedule.latitude = coords[0]
                schedule.longitude = coords[1]
        except:
            pass # Keep old coords or none if geocode fails
            
    # Auto-revert status from COMING_SOON to PENDING if rescheduled > 3 hours away
    # Status.COMING_SOON is "CS"
    if schedule.status == Status.COMING_SOON.value and schedule.meeting_start_time:
        try:
            st = arrow.get(schedule.meeting_start_time)
            # If start time is more than 3 hours from now
            if st > arrow.now().shift(hours=3):
                schedule.status = Status.PENDING.value
                print(f"DEBUG: Auto-reverted status to PENDING (Time > 3h away)")
        except Exception as e:
            print(f"DEBUG: Error checking time for status revert: {e}")
            
    updated_schedule = repo.update(schedule)
    
    # Update attends if provided
    if data.attends is not None:
        attends_data = data.attends
        # Delete existing attends
        # This requires a method in repo or direct session deletion
        from sqlmodel import delete
        from ...models.attend import attend
        session.exec(delete(attend).where(attend.schedule_id == schedule_id))
        
        # 1. Collect contact_ids to batch fetch linked user_ids
        contact_ids_to_fetch = []
        for att in attends_data:
            contact_id = att.contact_id
            # Normalize contact_id
            if isinstance(contact_id, str) and not contact_id.isdigit():
                 pass 
            elif contact_id is not None:
                 contact_ids_to_fetch.append(int(contact_id))
        
        # 2. Fetch Contacts map
        contact_user_map = {}
        contact_models_map = {}
        if contact_ids_to_fetch:
            from ...models.contact import Contact
            from sqlmodel import select
            statement = select(Contact).where(Contact.id.in_(contact_ids_to_fetch))
            contacts = session.exec(statement).all()
            for c in contacts:
                contact_models_map[c.id] = c
                if c.contact_user_id:
                    contact_user_map[c.id] = c.contact_user_id

        # Add new ones
        for att in attends_data:
            # Prioritize contact_user_id from a Contact object
            user_id = att.user_id
            contact_id = att.contact_id
            
            if isinstance(contact_id, str) and not contact_id.isdigit():
                 contact_id = None 
            elif contact_id is not None:
                 contact_id = int(contact_id)
            
            # If user_id is missing, try to get from contact map
            if not user_id and contact_id and contact_id in contact_user_map:
                user_id = contact_user_map[contact_id]

            new_attend = attend(
                schedule_id=schedule_id,
                user_id=user_id if user_id else None,
                contact_id=contact_id,
                status="P"
            )
            session.add(new_attend)
            
        session.commit()
        
        # Dispatch notifications for updates
        from sqlmodel import select
        updated_attends = session.exec(select(attend).where(attend.schedule_id == updated_schedule.schedule_id)).all()
        notification_service.notify_attendees(updated_schedule.title, updated_attends, contact_models_map)

    updated_schedule = repo.get_by_schedule_id(schedule_id) # Refresh to get latest state if needed
    result = updated_schedule.dict()
    print(f"DEBUG: update_schedule returning: {result}")
    return result

@router.post("/chat", response_model=ChatResponse)
def chat_schedule(
    request: ChatRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    user_message = request.message.strip()
    current_context = request.current_data
    
    # 1. 呼叫 AI 進行多輪對話處理
    ai_result = ai_service.process_conversation(user_message, current_context)
    
    updated_data = ai_result.get("updated_data", {})
    is_complete = ai_result.get("is_complete", False)
    ai_reply = ai_result.get("reply", "")
    
    saved_schedule = None

    # 2. 如果資訊完整，直接寫入資料庫
    if is_complete:
        try:
            print(f"DEBUG [chat]: is_complete=True, updated_data={updated_data}")
            
            # 轉換時間字串為 datetime 物件
            start_time_str = updated_data.get("start_time")
            print(f"DEBUG [chat]: start_time_str={start_time_str}")
            
            if not start_time_str:
                print("DEBUG [chat]: ERROR - start_time is missing from AI response!")
                return ChatResponse(
                    ai_reply=ai_reply + "\n\n(系統提示：AI 未回傳開始時間，行程未建立)",
                    updated_data=updated_data,
                    is_complete=False
                )
                
            participants = updated_data.get("participants", [])
            if not participants or (isinstance(participants, list) and len(participants) == 0) or (isinstance(participants, str) and not participants.strip()):
                print("DEBUG [chat]: ERROR - participants is missing from AI response!")
                return ChatResponse(
                    ai_reply=ai_reply + "\n\n(系統提示：您尚未指定聯絡人，請使用 @ 標記指定您的聯絡人，例如：和 @小明 開會)",
                    updated_data=updated_data,
                    is_complete=False
                )
            
            start_time = datetime.fromisoformat(start_time_str)
            
            # 預設結束時間為 1 小時後，如果沒有指定
            end_time_str = updated_data.get("end_time")
            if end_time_str:
                end_time = datetime.fromisoformat(end_time_str)
            else:
                end_time = start_time.replace(hour=start_time.hour + 1) # Default 1 hour

            repo = ScheduleRepository(session)

            # 3. 檢查衝突 (Conflict Detection)
            if not request.force_create:
                conflicts = repo.find_overlapping(current_user.user_id, start_time, end_time)
                if conflicts:
                    # Found conflicts (could be multiple)
                    conflict_details = []
                    for c in conflicts:
                        p_start = arrow.get(c.meeting_start_time).format('HH:mm')
                        p_end = arrow.get(c.meeting_end_time).format('HH:mm') if c.meeting_end_time else "??"
                        conflict_details.append(f"{p_start}-{p_end}「{c.title}」")
                    
                    conflict_msg = "、".join(conflict_details)
                    
                    # Store the first conflict for the structured return (frontend might use it for navigation)
                    # But the message should list all.
                    base_conflict = conflicts[0]
                    
                    return ChatResponse(
                        ai_reply=f"時間衝突！您在該時段已有：{conflict_msg}。您確定這個時間正確嗎？",
                        updated_data=updated_data,
                        is_complete=True, # Logic complete, but blocked by conflict
                        conflict={
                            "title": base_conflict.title,
                            "start_time": base_conflict.meeting_start_time.isoformat(),
                            "end_time": base_conflict.meeting_end_time.isoformat() if base_conflict.meeting_end_time else None
                        }
                    )

            # 建立 Schedule 物件
            new_schedule = Schedule(
                user_id=current_user.user_id,
                title=updated_data.get("title", "未命名行程"),
                description=updated_data.get('description', ''),
                meeting_start_time=start_time,
                meeting_end_time=end_time,
                # meeting_time removed
                meeting_location=updated_data.get("location"),
                location=updated_data.get("location"),
                status=Status.PENDING.value
            )
            
            # 地理編碼 (Optional)
            if new_schedule.meeting_location:
                 # Pass user's current location to bias the search (e.g. find nearest 7-11)
                 coords = HereService.get_coordinates(
                     new_schedule.meeting_location, 
                     lat=request.latitude, 
                     lon=request.longitude
                 )
                 if coords:
                     new_schedule.latitude = coords[0]
                     new_schedule.longitude = coords[1]

            saved_schedule_obj = repo.create(new_schedule)
            saved_schedule = saved_schedule_obj.dict()
            print(f"DEBUG [chat]: Schedule created successfully! ID={saved_schedule_obj.schedule_id}")
            
            # 如果有參與者，這邊處理 attend 表
            participants = updated_data.get("participants", [])
            # Handle cases where participants might be a string
            if isinstance(participants, str):
                 participants = [p.strip() for p in participants.split(",")]
                 
            if participants and isinstance(participants, list):
                from ...models.contact import Contact
                from ...models.attend import attend
                from sqlmodel import select
                
                for p_name in participants:
                    if not p_name.strip(): continue
                    # Clean up random characters like '@'
                    clean_name = p_name.strip().lstrip('@')
                    
                    # 1. 尋找現有聯絡人
                    existing_contact = session.exec(
                        select(Contact).where(
                            Contact.user_id == current_user.user_id,
                            Contact.nick_name == clean_name
                        )
                    ).first()
                    
                    contact_id = None
                    if existing_contact:
                        contact_id = existing_contact.id
                        print(f"DEBUG [chat]: Found existing contact for '{clean_name}': {contact_id}")
                    else:
                        # 2. 自動建立聯絡人
                        new_contact = Contact(
                            user_id=current_user.user_id,
                            nick_name=clean_name
                        )
                        session.add(new_contact)
                        session.commit()
                        session.refresh(new_contact)
                        contact_id = new_contact.id
                        print(f"DEBUG [chat]: Auto-created contact for '{clean_name}': {contact_id}")
                    
                    # 3. 綁定 attend
                    new_attend = attend(
                        schedule_id=saved_schedule_obj.schedule_id,
                        contact_id=contact_id,
                        status="P"
                    )
                    session.add(new_attend)
                session.commit()
            
        except Exception as e:
            print(f"Error creating schedule: {e}")
            import traceback
            traceback.print_exc()
            return ChatResponse(
                ai_reply=f"資訊已收集完成，但在建立行程時發生錯誤：{str(e)}",
                updated_data=updated_data,
                is_complete=True # 雖然失敗但邏輯上是對話結束
            )

    # 3. 回傳結果
    return ChatResponse(
        ai_reply=ai_reply,
        updated_data=updated_data, # 把這個傳回給前端，前端下次要帶回來
        is_complete=is_complete,
        schedule=saved_schedule
    )