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
from ...services.schedule_graph import schedule_graph
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
            
            is_online=data.is_online or False,

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
            
        start_time_str = schedule_data.get("start_time")
        if not start_time_str:
            raise HTTPException(status_code=400, detail="無法從訊息中辨識出時間，請提供包含時間的行程內容。")
        
        meeting_start_time = datetime.fromisoformat(start_time_str)
        
        end_time_str = schedule_data.get("end_time")
        if end_time_str:
            meeting_end_time = datetime.fromisoformat(end_time_str)
        else:
            meeting_end_time = meeting_start_time.replace(hour=meeting_start_time.hour + 1)
            
        # Create Schedule object
        schedule = Schedule(
            user_id=current_user.user_id,
            title=schedule_data.get("title", "未命名行程"),
            meeting_start_time=meeting_start_time,
            meeting_end_time=meeting_end_time,
            meeting_location=schedule_data.get("location"),
            location=schedule_data.get("location"),
            description=schedule_data.get("description")
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
        
        # 2. Fetch Contacts map and auto-link to users by email
        contact_user_map = {}
        contact_models_map = {}
        if contact_ids_to_fetch:
            from ...models.contact import Contact
            from sqlmodel import select
            statement = select(Contact).where(Contact.id.in_(contact_ids_to_fetch))
            contacts = session.exec(statement).all()
            for c in contacts:
                contact_models_map[c.id] = c
                # Auto-link contact to user by email if not already linked
                if not c.contact_user_id and c.email:
                    matched_user = session.exec(select(User).where(User.email == c.email)).first()
                    if matched_user:
                        c.contact_user_id = matched_user.user_id
                        session.add(c)
                        session.commit()
                        session.refresh(c)
                        print(f"DEBUG: Auto-linked contact {c.id} to user {matched_user.user_id} via email {c.email}")
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
        # Build users_map so notification_service can look up user emails
        users_map = {}
        user_ids_to_fetch = list(contact_user_map.values())
        if user_ids_to_fetch:
            fetched_users = session.exec(select(User).where(User.user_id.in_(user_ids_to_fetch))).all()
            for u in fetched_users:
                users_map[u.user_id] = u
        notification_service.notify_attendees(
            created_schedule, created_attends, contact_models_map,
            users_map=users_map, inviter_name=current_user.full_name or "某人"
        )

    return created_schedule.dict()

@router.post("/fix-contact-links")
def fix_contact_links(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """
    Backfill: 對所有 contact.email 能找到 user.email 的聯絡人，補上 contact_user_id 和 attend.user_id。
    """
    from sqlmodel import select as sql_select
    from ...models.contact import Contact

    updated_contacts = 0
    updated_attends = 0

    # 1. 找出所有有 email 但沒有 contact_user_id 的 contact
    contacts = session.exec(
        sql_select(Contact).where(Contact.email.isnot(None), Contact.contact_user_id.is_(None))
    ).all()

    for c in contacts:
        matched_user = session.exec(sql_select(User).where(User.email == c.email)).first()
        if matched_user:
            c.contact_user_id = matched_user.user_id
            session.add(c)
            updated_contacts += 1

    session.commit()

    # 2. 找出所有 attend.user_id 是 NULL 但 contact 已有 contact_user_id 的記錄
    attends = session.exec(sql_select(attend).where(attend.user_id.is_(None), attend.contact_id.isnot(None))).all()
    for a in attends:
        contact = session.get(Contact, a.contact_id)
        if contact and contact.contact_user_id:
            a.user_id = contact.contact_user_id
            session.add(a)
            updated_attends += 1

    session.commit()

    return {
        "updated_contacts": updated_contacts,
        "updated_attends": updated_attends,
        "message": f"已補上 {updated_contacts} 筆 contact 連結，{updated_attends} 筆 attend 連結"
    }


@router.get("/rsvp")
def rsvp_schedule(token: str, action: str, session: Session = Depends(get_session)):
    """
    Handle RSVP links sent via email.
    token = attend_id (UUID)
    action = "accept" | "decline"
    """
    from sqlmodel import select as sql_select

    if action not in ("accept", "decline"):
        raise HTTPException(status_code=400, detail="Invalid action. Use 'accept' or 'decline'.")

    # Look up the attend record by attend_id
    attend_record = session.exec(sql_select(attend).where(attend.attend_id == token)).first()
    if not attend_record:
        raise HTTPException(status_code=404, detail="Invitation not found or already expired.")

    # Fetch the schedule
    repo = ScheduleRepository(session)
    schedule = repo.get_by_schedule_id(attend_record.schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found.")

    if action == "accept":
        attend_record.status = "AT"
        session.add(attend_record)
        session.commit()
        return {"message": f"您已接受「{schedule.title}」的邀請！", "status": "accepted"}

    # action == "decline"
    attend_record.status = "NG"
    session.add(attend_record)
    session.commit()

    # Notify the schedule creator
    creator = session.exec(sql_select(User).where(User.user_id == schedule.user_id)).first()
    if creator:
        # Get attendee display name
        attendee_name = "受邀者"
        if attend_record.contact_id:
            from ...models.contact import Contact
            contact = session.get(Contact, attend_record.contact_id)
            if contact:
                attendee_name = contact.nick_name or attendee_name
        elif attend_record.user_id:
            invitee = session.exec(sql_select(User).where(User.user_id == attend_record.user_id)).first()
            if invitee:
                attendee_name = invitee.full_name or attendee_name

        notification_service.notify_creator_of_decline(schedule, attendee_name, creator)

    return {"message": f"您已拒絕「{schedule.title}」的邀請，活動建立者已收到通知。", "status": "declined"}


@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Delete a schedule and all related attend records."""
    from sqlmodel import delete as sql_delete
    from ...models.attend import attend

    repo = ScheduleRepository(session)
    schedule = repo.get_by_schedule_id(schedule_id)

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Delete attend records first (FK constraint)
    session.exec(sql_delete(attend).where(attend.schedule_id == schedule_id))
    session.delete(schedule)
    session.commit()

    return {"ok": True}


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
    if data.is_online is not None: schedule.is_online = data.is_online
    
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
        
        # 2. Fetch Contacts map and auto-link to users by email
        contact_user_map = {}
        contact_models_map = {}
        if contact_ids_to_fetch:
            from ...models.contact import Contact
            from sqlmodel import select
            statement = select(Contact).where(Contact.id.in_(contact_ids_to_fetch))
            contacts = session.exec(statement).all()
            for c in contacts:
                contact_models_map[c.id] = c
                # Auto-link contact to user by email if not already linked
                if not c.contact_user_id and c.email:
                    matched_user = session.exec(select(User).where(User.email == c.email)).first()
                    if matched_user:
                        c.contact_user_id = matched_user.user_id
                        session.add(c)
                        session.commit()
                        session.refresh(c)
                        print(f"DEBUG: Auto-linked contact {c.id} to user {matched_user.user_id} via email {c.email}")
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
        # Build users_map so notification_service can look up user emails
        users_map = {}
        user_ids_to_fetch = list(contact_user_map.values())
        if user_ids_to_fetch:
            fetched_users = session.exec(select(User).where(User.user_id.in_(user_ids_to_fetch))).all()
            for u in fetched_users:
                users_map[u.user_id] = u
        notification_service.notify_attendees(
            updated_schedule, updated_attends, contact_models_map,
            users_map=users_map, inviter_name=current_user.full_name or "某人"
        )

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
    current_context = request.current_data or {}

    saved_schedule = None

    # ── confirm_delete=True: user confirmed deletion ──────────────────────────
    if request.confirm_delete:
        delete_id = current_context.get("delete_schedule_id")
        if not delete_id:
            return ChatResponse(ai_reply="找不到要刪除的行程。", updated_data=current_context, is_complete=False)
        from sqlmodel import delete as sql_delete
        repo = ScheduleRepository(session)
        target = repo.get_by_schedule_id(delete_id)
        if not target or target.user_id != current_user.user_id:
            return ChatResponse(ai_reply="找不到行程或無權限刪除。", updated_data=current_context, is_complete=False)
        session.execute(sql_delete(attend).where(attend.schedule_id == delete_id))
        session.delete(target)
        session.commit()
        return ChatResponse(
            ai_reply=f"✅ 已刪除行程「{target.title}」。",
            updated_data={},
            is_complete=True,
            schedule_deleted=True,
        )

    # ── Pre-match schedules with Python keyword search ────────────────────────
    # Reliable fuzzy matching before handing to AI — avoids AI missing titles
    def _python_match_schedules(message: str, schedules: list) -> list:
        """Return schedule list with matching ones tagged [最佳匹配]."""
        if not schedules:
            return schedules
        # Strip common intent words to get the core keyword
        stop_words = {"取消", "刪除", "刪掉", "移除", "更改", "修改", "調整", "把", "的", "行程",
                      "活動", "我", "這個", "請", "幫我", "改到", "延後", "提早"}
        words = [w for w in message if w not in stop_words and len(w.strip()) > 0]
        keyword = "".join(words)  # full message minus stop words

        tagged = []
        for s in schedules:
            title = s.get("title", "")
            # Check if any 2+ char substring of keyword appears in title
            matched = False
            for length in range(len(keyword), 1, -1):
                for start in range(len(keyword) - length + 1):
                    chunk = keyword[start:start + length]
                    if len(chunk) >= 2 and chunk in title:
                        matched = True
                        break
                if matched:
                    break
            if matched:
                s = dict(s)
                s["_match"] = True
                tagged.append(s)
            else:
                tagged.append(s)
        return tagged

    annotated_schedule_list = _python_match_schedules(user_message, request.schedule_list or [])

    # ── confirm_location=True: user already approved a location ──────────────
    # Skip the graph entirely. Re-running AI on "確認地點：XX" confuses the model.
    if request.confirm_location:
        updated_data = current_context
        is_complete = True
        ai_reply = ""
        needs_location_confirm = False
        location_candidates: list = []
        location_details = None
        intent = "create"
        target_schedule_id = current_context.get("target_schedule_id")
    else:
        # ── Run LangGraph: collect_info → validate_location ──────────────────
        graph_state = schedule_graph.invoke({
            "user_message": user_message,
            "conversation_history": request.conversation_history or [],
            "current_data": current_context,
            "user_lat": request.latitude,
            "user_lon": request.longitude,
            "schedule_list": annotated_schedule_list,
            # defaults for output fields
            "updated_data": {},
            "missing_fields": [],
            "is_complete": False,
            "reply": "",
            "intent": "create",
            "target_schedule_id": None,
            "location_result": None,
            "needs_location_confirm": False,
            "location_candidates": [],
            "location_details": None,
        })

        updated_data = graph_state["updated_data"]
        is_complete = graph_state["is_complete"]
        ai_reply = graph_state["reply"]
        needs_location_confirm = graph_state["needs_location_confirm"]
        location_candidates = graph_state["location_candidates"]
        location_details = graph_state["location_details"]
        intent = graph_state.get("intent", "create")
        target_schedule_id = graph_state.get("target_schedule_id")

        # ── Delete intent: return confirm prompt to frontend ──────────────────
        if intent == "delete":
            delete_ctx = dict(current_context)
            delete_ctx["delete_schedule_id"] = target_schedule_id
            # Find schedule details for display
            confirm_info = None
            if target_schedule_id:
                repo = ScheduleRepository(session)
                del_target = repo.get_by_schedule_id(target_schedule_id)
                if del_target:
                    confirm_info = {
                        "id": target_schedule_id,
                        "title": del_target.title,
                        "start_time": del_target.meeting_start_time.isoformat() if isinstance(del_target.meeting_start_time, datetime) else str(del_target.meeting_start_time) if del_target.meeting_start_time else None,
                    }
            return ChatResponse(
                ai_reply=ai_reply,
                updated_data=delete_ctx,
                is_complete=False,
                confirm_delete=confirm_info,
            )

        # ── Return early if location needs user input ─────────────────────────
        if needs_location_confirm:
            return ChatResponse(
                ai_reply=ai_reply,
                updated_data=updated_data,
                is_complete=is_complete,
                needs_location_confirm=True,
                location_candidates=location_candidates if location_candidates else None,
                location_details=location_details,
            )

        # ── Still gathering info — return AI reply ────────────────────────────
        if not is_complete:
            return ChatResponse(
                ai_reply=ai_reply,
                updated_data=updated_data,
                is_complete=False,
            )

    # ── is_complete=True — proceed to DB creation ────────────────────────────
    if is_complete:
        try:
            print(f"DEBUG [chat]: is_complete=True, updated_data={updated_data}")

            start_time_str = updated_data.get("start_time")
            print(f"DEBUG [chat]: intent={intent}, start_time_str={start_time_str}")

            # For create: start_time is mandatory. For edit: it may be absent (only other fields changed).
            if not start_time_str and intent != "edit":
                return ChatResponse(
                    ai_reply="請問行程預計安排在什麼時間呢？",
                    updated_data=updated_data,
                    is_complete=False,
                )

            if start_time_str:
                start_time = datetime.fromisoformat(start_time_str)
                end_time_str = updated_data.get("end_time")
                if end_time_str:
                    end_time = datetime.fromisoformat(end_time_str)
                else:
                    end_time = start_time.replace(hour=min(start_time.hour + 1, 23))
            else:
                # edit without time change — will be filled from existing record
                start_time = None
                end_time = None

            location_name = updated_data.get("location")
            location_lat = None
            location_lon = None

            if location_name:
                # confirm_location=True: coords come from context (set by frontend on selection)
                ctx_lat = updated_data.get("latitude") or updated_data.get("lat")
                ctx_lon = updated_data.get("longitude") or updated_data.get("lon")
                if ctx_lat and ctx_lon:
                    location_lat = float(ctx_lat)
                    location_lon = float(ctx_lon)
                elif request.latitude and request.longitude:
                    location_lat = request.latitude
                    location_lon = request.longitude

            repo = ScheduleRepository(session)

            # 3. 檢查衝突 (Conflict Detection — only for create, skip for edit)
            if not request.force_create and intent != "edit" and start_time:
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
                            "start_time": base_conflict.meeting_start_time.isoformat() if isinstance(base_conflict.meeting_start_time, datetime) else str(base_conflict.meeting_start_time),
                            "end_time": base_conflict.meeting_end_time.isoformat() if base_conflict.meeting_end_time else None
                        }
                    )

            # ── Update existing schedule (chat edit intent or correction) ──────
            effective_schedule_id = request.schedule_id or (target_schedule_id if intent == "edit" else None)
            if effective_schedule_id:
                existing = repo.get_by_schedule_id(effective_schedule_id)
                if existing and existing.user_id == current_user.user_id:
                    # Only update fields that were explicitly provided in updated_data
                    if updated_data.get("title"): existing.title = updated_data["title"]
                    if updated_data.get("description"): existing.description = updated_data["description"]
                    if updated_data.get("start_time"):
                        existing.meeting_start_time = start_time
                        existing.meeting_end_time = end_time
                    if location_name:
                        existing.meeting_location = location_name
                        existing.location = location_name
                    if location_lat and location_lon:
                        existing.latitude = location_lat
                        existing.longitude = location_lon
                    saved_schedule_obj = repo.update(existing)
                    saved_schedule = saved_schedule_obj.dict()
                    ai_reply = f"✅ 已為您更新行程「{existing.title}」！"
                    print(f"DEBUG [chat]: Schedule updated ID={effective_schedule_id}")
                else:
                    return ChatResponse(
                        ai_reply="找不到行程，無法修改。",
                        updated_data=updated_data,
                        is_complete=False,
                    )
            else:
                # ── 建立 Schedule 物件 ─────────────────────────────────────────
                new_schedule = Schedule(
                    user_id=current_user.user_id,
                    title=updated_data.get("title", "未命名行程"),
                    description=updated_data.get('description', ''),
                    meeting_start_time=start_time,
                    meeting_end_time=end_time,
                    meeting_location=location_name,
                    location=location_name,
                    latitude=location_lat,
                    longitude=location_lon,
                    status=Status.PENDING.value
                )
                saved_schedule_obj = repo.create(new_schedule)
                saved_schedule = saved_schedule_obj.dict()
                print(f"DEBUG [chat]: Schedule created successfully! ID={saved_schedule_obj.schedule_id}")
                ai_reply = f"✅ 已為您建立行程「{updated_data.get('title', '未命名行程')}」！"
            
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
                ai_reply="行程建立失敗，請稍後再試。",
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