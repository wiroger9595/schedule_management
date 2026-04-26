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
from ...schemas.schedule import ScheduleCreate, ScheduleUpdate, StatusUpdate, ChatMessage, ChatRequest, ChatResponse, FeedbackRequest
from ...models.ai_feedback import AIFeedback
from ...services.schedule_graph import schedule_graph
from ...services.chat_utils import (
    extract_person_hint as _extract_person_hint,
    check_person_in_contacts as _check_person_in_contacts,
    validate_output as _validate_output,
    fmt_schedule_summary as _fmt_schedule_summary,
    python_match_schedules as _python_match_schedules,
)
from ...services.attend_service import (
    add_participants as _add_participants,
    remove_participants as _remove_participants,
)
from .auth import get_current_user


from ...services.ai_policy import build_schedule_list_reply as _build_schedule_list_reply


router = APIRouter()

@router.get("/", response_model=List[dict])
@router.get("", response_model=List[dict], include_in_schema=False)
def get_schedules(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = ScheduleRepository(session)
    schedules = repo.get_by_user_id(current_user.user_id)
    results = [s.dict() for s in schedules]

    # Annotate each schedule with is_owner + creator_name
    creator_ids = {r["user_id"] for r in results if r.get("user_id") and r["user_id"] != current_user.user_id}
    creator_names: dict[str, str] = {}
    if creator_ids:
        from sqlmodel import select as _sel
        _users = session.exec(_sel(User).where(User.user_id.in_(list(creator_ids)))).all()
        creator_names = {u.user_id: u.full_name or u.email or u.user_id for u in _users}

    for r in results:
        r["is_owner"] = r.get("user_id") == current_user.user_id
        r["creator_name"] = None if r["is_owner"] else creator_names.get(r.get("user_id", ""), "其他人")

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
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="您不是此行程的建立者，無法修改")

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
            
    # Auto-revert status to PENDING when time is rescheduled to the future
    _revertable = {Status.COMING_SOON.value, "NA"}  # CS and notAttended
    if schedule.status in _revertable and schedule.meeting_start_time:
        try:
            from .chat_utils import _to_taipei as _ttp2
            _st_tw = _ttp2(schedule.meeting_start_time)
            _now_tw = arrow.now("Asia/Taipei")
            if _st_tw and _st_tw > _now_tw.shift(hours=3):
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

@router.post("/reindex", response_model=dict)
def reindex_embeddings(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """重建用戶所有行程的 embedding。首次部署或更換 embedding 模型後使用。"""
    from ...services.embedding_service import EmbeddingService
    repo = ScheduleRepository(session)
    schedules = repo.get_by_user_id(current_user.user_id)
    success, failed = 0, 0
    for s in schedules:
        try:
            emb = EmbeddingService.embed_schedule(
                s.title or "",
                s.meeting_location or "",
                s.description or "",
            )
            repo.upsert_embedding(s.schedule_id, emb)
            success += 1
        except Exception as e:
            print(f"[reindex] {s.schedule_id} failed: {e}")
            failed += 1
    print(f"[reindex] user={current_user.user_id} success={success} failed={failed}")
    return {"success": success, "failed": failed, "total": len(schedules)}


@router.post("/chat/clear")
def clear_chat_history(current_user: User = Depends(get_current_user)):
    """清除用戶的 AI 對話紀錄與行程 context（對應 Flutter clearChat）"""
    from ...core.redis_client import redis_client
    user_id = str(current_user.user_id)
    redis_client.clear_chat_history(user_id)
    redis_client.clear_chat_context(user_id)
    return {"ok": True}


@router.post("/chat", response_model=ChatResponse)
def chat_schedule(
    request: ChatRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    from ...core.redis_client import redis_client

    user_message = request.message.strip()
    user_id = str(current_user.user_id)

    # ── Rate limit: 每10秒最多3次 AI 請求 ────────────────────────────────────
    if not request.confirm_delete and not request.confirm_location and not request.confirm_past_edit:
        if not redis_client.check_ai_rate_limit(user_id):
            return ChatResponse(
                ai_reply="請求太頻繁，請稍等一下再繼續。",
                updated_data=request.current_data or {},
                is_complete=False,
            )

    # ── 從 Redis 讀取 server-side history，Flutter 帶的 history 為備用 ────────
    server_history = redis_client.get_chat_history(user_id)
    conversation_history = server_history if server_history else (request.conversation_history or [])

    current_context = request.current_data or {}

    saved_schedule = None

    # ── confirm_delete=True: user confirmed deletion ──────────────────────────
    if request.confirm_delete:
        delete_id = current_context.get("delete_schedule_id")
        if not delete_id:
            _del_msg = _build_schedule_list_reply(
                "請問您要刪除哪個行程呢？", request.schedule_list or []
            )
            return ChatResponse(ai_reply=_del_msg, updated_data=current_context, is_complete=False)
        from sqlmodel import delete as sql_delete
        repo = ScheduleRepository(session)
        target = repo.get_by_schedule_id(delete_id)
        if not target or target.user_id != current_user.user_id:
            _del_msg2 = _build_schedule_list_reply(
                "找不到可刪除的行程（可能已刪除或非您建立），請選擇要刪除的行程：",
                request.schedule_list or [],
            )
            return ChatResponse(ai_reply=_del_msg2, updated_data=current_context, is_complete=False)
        session.execute(sql_delete(attend).where(attend.schedule_id == delete_id))
        session.delete(target)
        session.commit()
        return ChatResponse(
            ai_reply=f"✅ 已刪除行程「{target.title}」。",
            updated_data={},
            is_complete=True,
            schedule_deleted=True,
        )

    annotated_schedule_list = _python_match_schedules(user_message, request.schedule_list or [])

    # ── Semantic Router：偵測「列出/計數」意圖 → 強制帶入完整清單，跳過語意過濾 ──
    _LIST_KEYWORDS = {"幾個", "幾件", "幾筆", "所有", "全部", "列出", "顯示", "查看", "有哪些", "有什麼", "清單", "總共", "列一下"}
    _is_list_query = any(kw in user_message for kw in _LIST_KEYWORDS)

    # ── Pre-compute query embedding once (shared by hybrid + contact search) ──
    _query_emb: list | None = None
    try:
        from ...services.embedding_service import EmbeddingService as _ES_pre
        _query_emb = _ES_pre.embed(user_message)
    except Exception as _pre_emb_err:
        print(f"[embedding] pre-compute skipped (non-critical): {_pre_emb_err}")

    # ── Hybrid Search + Reranking ─────────────────────────────────────────────
    # 語意搜尋 + 關鍵字結果合併，依 cosine 分數重排，過濾低相關行程
    try:
        from ...repositories.schedule_repository import ScheduleRepository as _Repo
        if _query_emb is None:
            raise RuntimeError("embedding unavailable, skip hybrid search")
        _repo = _Repo(session)
        query_emb = _query_emb
        semantic_results = _repo.semantic_search(user_id, query_emb, top_k=10)

        # {schedule_id: similarity_score}
        similarity_map = {s.schedule_id: score for s, score in semantic_results}
        semantic_ids = set(similarity_map.keys())
        SIMILARITY_THRESHOLD = 0.3

        # Flutter 傳來的原始清單 id — 這些行程一律保留，不過濾
        original_ids = {s.get("schedule_id") or s.get("id", "") for s in (request.schedule_list or [])}

        final_list = []
        for s in annotated_schedule_list:
            sid = s.get("schedule_id") or s.get("id", "")
            sim = similarity_map.get(sid, 0.0)
            is_keyword_match = s.get("_match", False)

            if sid in semantic_ids or is_keyword_match:
                s = dict(s)
                s["_match"] = True
                s["_similarity"] = round(sim, 4)

            # 「列出/計數」類查詢強制保留全部原始清單，其餘才做語意過濾
            is_original = sid in original_ids
            has_embedding = sid in similarity_map
            should_filter = (not _is_list_query) and (not is_original) and has_embedding and (not is_keyword_match) and (sim < SIMILARITY_THRESHOLD)
            if not should_filter:
                final_list.append(s)

        # 補上語意搜尋找到但不在原清單的歷史行程（分數須達標）
        existing_ids = {s.get("schedule_id") or s.get("id", "") for s in final_list}
        for s_obj, score in semantic_results:
            if s_obj.schedule_id not in existing_ids and score >= SIMILARITY_THRESHOLD:
                s_dict = s_obj.dict()
                s_dict["_match"] = True
                s_dict["_similarity"] = round(score, 4)
                final_list.append(s_dict)

        # Rerank：_match 優先，同層依 similarity 降序
        final_list.sort(
            key=lambda x: (1 if x.get("_match") else 0, x.get("_similarity", 0.0)),
            reverse=True,
        )
        annotated_schedule_list = final_list
        print(f"[hybrid_search] query='{user_message[:20]}' "
              f"results={len(final_list)} semantic_hits={len(semantic_ids)}")
    except Exception as _sem_err:
        print(f"[semantic_search] skipped (non-critical): {_sem_err}")
        # PostgreSQL transaction 可能已進入 aborted 狀態，必須 rollback
        # 否則後續同一 session 的所有操作都會失敗（InFailedSqlTransaction）
        try:
            session.rollback()
        except Exception:
            pass

    # ── Contact semantic search + User memory retrieval ──────────────────────
    # 在 hybrid search 之後，把聯絡人語意結果和記憶片段注入 AI context
    _contact_hints: list = []
    _memory_snippets: list = []
    try:
        from ...repositories.schedule_repository import ScheduleRepository as _Repo2
        if _query_emb is None:
            raise RuntimeError("embedding unavailable, skip contact/memory search")
        _repo2 = _Repo2(session)

        # 聯絡人語意搜尋
        _contact_hints = _repo2.semantic_search_contacts(user_id, _query_emb, top_k=4, min_similarity=0.4)

        # 用戶記憶搜尋
        _memory_snippets = _repo2.search_user_memory(user_id, _query_emb, top_k=3, min_similarity=0.45)

        if _contact_hints:
            print(f"[contact_search] matches={[c['nick_name'] for c in _contact_hints]}")
            # 偵測同名聯絡人
            _hint_names = [c["nick_name"] for c in _contact_hints if c["nick_name"]]
            if _hint_names:
                _dup_map = _repo2.find_duplicate_contacts(user_id, _hint_names)
                if _dup_map:
                    for _n, _entries in _dup_map.items():
                        current_context[f"_dup_{_n}"] = _entries
                    print(f"[contact_search] duplicates={list(_dup_map.keys())}")
        if _memory_snippets:
            print(f"[memory_search] hits={len(_memory_snippets)}")
    except Exception as _cs_err:
        print(f"[contact/memory search] skipped (non-critical): {_cs_err}")
        try:
            session.rollback()
        except Exception:
            pass

    # ── Affirmative text reply when location confirm is pending ──────────────
    # User typed "是的" / "對" instead of clicking the card button.
    # Detect and treat as confirm_location=True using stored coords.
    _AFFIRMATIVE = {"是", "是的", "對", "好", "確認", "確定", "ok", "OK", "yes", "沒錯", "正確", "行", "可以"}
    _pending_lat = current_context.get("_pending_confirm_lat")
    _pending_lon = current_context.get("_pending_confirm_lon")
    if (user_message.strip() in _AFFIRMATIVE and _pending_lat and _pending_lon):
        request = request.model_copy(update={
            "confirm_location": True,
            "latitude": _pending_lat,
            "longitude": _pending_lon,
        })

    # ── Auto-confirm past-edit when user continues typing after warning ───────
    # If _pending_past_edit_id is stored in context (guard already shown once),
    # treat any subsequent user message as implicit confirmation to proceed.
    _pending_past_id = current_context.get("_pending_past_edit_id")
    if _pending_past_id and not request.confirm_past_edit:
        request = request.model_copy(update={"confirm_past_edit": True})

    # ── confirm_past_edit=True: user approved editing a past schedule ────────
    # Skip the graph — location was already validated in the previous turn.
    # Re-running the graph would re-trigger location confirmation.
    if request.confirm_past_edit and current_context.get("_pending_past_edit_id"):
        updated_data = {k: v for k, v in current_context.items() if not k.startswith("_")}
        is_complete = True
        ai_reply = ""
        needs_location_confirm = False
        location_candidates: list = []
        location_details = None
        location_not_found = False
        intent = "edit"
        target_schedule_id = current_context.get("_pending_past_edit_id")

    # ── confirm_location=True: user already approved a location ──────────────
    # Skip the graph entirely. Re-running AI on "確認地點：XX" confuses the model.
    elif request.confirm_location:
        # Strip all internal _ keys (including _pending_confirm_*)
        updated_data = {k: v for k, v in current_context.items() if not k.startswith("_")}
        is_complete = True
        ai_reply = ""
        needs_location_confirm = False
        location_candidates: list = []
        location_details = None
        location_not_found = False
        # If pending edit, resume edit intent instead of creating
        pending_edit_id = current_context.get("_pending_edit_schedule_id")
        if pending_edit_id:
            intent = "edit"
            target_schedule_id = pending_edit_id
        else:
            intent = "create"
            target_schedule_id = current_context.get("target_schedule_id")
    else:
        # ── Semantic Router: 本地預分類 intent（減少 AI 呼叫）────────────────
        pre_intent: str | None = None
        try:
            from ...services.semantic_router_service import semantic_router
            route_result = semantic_router.route(user_message)
            if route_result["confidence"] >= 0.55:  # 高信心才預注入
                pre_intent = route_result["intent"]
                print(f"[SemanticRouter] pre_intent={pre_intent} conf={route_result['confidence']}")
        except Exception:
            pass

        # ── Run LangGraph: collect_info → validate_location ──────────────────
        try:
            graph_state = schedule_graph.invoke({
                "user_message": user_message,
                "conversation_history": conversation_history,
                "current_data": {
                    **current_context,
                    **({"_pre_intent": pre_intent} if pre_intent else {}),
                    **({"_contact_hints": _contact_hints} if _contact_hints else {}),
                    **({"_memory_snippets": _memory_snippets} if _memory_snippets else {}),
                },
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
        except RuntimeError as _rt_err:
            if "AI_RATE_LIMITED" in str(_rt_err):
                return ChatResponse(
                    ai_reply="系統目前很忙，請稍後幾秒再試 🙏",
                    updated_data=current_context,
                    is_complete=False,
                )
            import traceback; traceback.print_exc()
            return ChatResponse(
                ai_reply="AI 處理失敗，請重新發送訊息。",
                updated_data=current_context,
                is_complete=False,
            )
        except Exception as _graph_err:
            print(f"[chat] graph error: {_graph_err}")
            import traceback; traceback.print_exc()
            err_str = str(_graph_err)
            if "429" in err_str or "queue_exceeded" in err_str or "rate" in err_str.lower():
                return ChatResponse(
                    ai_reply="系統目前很忙，請稍後幾秒再試 🙏",
                    updated_data=current_context,
                    is_complete=False,
                )
            return ChatResponse(
                ai_reply="AI 處理失敗，請重新發送訊息。",
                updated_data=current_context,
                is_complete=False,
            )

        updated_data = graph_state["updated_data"]
        is_complete = graph_state["is_complete"]
        ai_reply = graph_state["reply"]
        needs_location_confirm = graph_state["needs_location_confirm"]
        location_candidates = graph_state["location_candidates"]
        location_details = graph_state["location_details"]
        location_not_found = graph_state.get("location_not_found", False)
        intent = graph_state.get("intent", "create")
        target_schedule_id = graph_state.get("target_schedule_id")

        # ── Delete intent: return confirm prompt to frontend ──────────────────
        if intent == "delete":
            # Validate mentioned person exists in contacts
            _ph = _extract_person_hint(user_message)
            if _ph and not _check_person_in_contacts(user_id, _ph, session):
                return ChatResponse(
                    ai_reply=f"聯絡人中沒有「{_ph}」，請確認名稱是否正確。",
                    updated_data={}, is_complete=False,
                )
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

        # ── Edit intent: validate mentioned person exists in contacts ────────
        # 必須在 is_complete gate 之前執行，否則 AI ask_user 回傳 is_complete=False
        # 時就直接 return，第二輪 follow-up 又因 _pending_edit_schedule_id 跳過驗證
        if intent == "edit" and not current_context.get("_pending_edit_schedule_id"):
            _ph = _extract_person_hint(user_message)
            if _ph and not _check_person_in_contacts(user_id, _ph, session):
                return ChatResponse(
                    ai_reply=f"聯絡人中沒有「{_ph}」，請確認名稱是否正確。",
                    updated_data={}, is_complete=False,
                )

        # ── Return early if location needs user input ─────────────────────────
        if needs_location_confirm:
            # Embed confirmed coords into updated_data so that if the user
            # types an affirmative reply ("是的") instead of clicking the button,
            # the next turn can short-circuit without re-running HERE validation.
            _loc_data = dict(updated_data)
            if location_details:
                _loc_data["_pending_confirm_lat"] = location_details.get("lat")
                _loc_data["_pending_confirm_lon"] = location_details.get("lon")
                _loc_data["_pending_confirm_name"] = location_details.get("name")
            elif location_candidates:
                pass  # multiple candidates: user must click, no single coord to store
            return ChatResponse(
                ai_reply=ai_reply,
                updated_data=_loc_data,
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
                location_not_found=location_not_found,
            )

    # ── is_complete=True — proceed to DB creation ────────────────────────────
    if is_complete:
        try:
            print(f"DEBUG [chat]: is_complete=True, updated_data={updated_data}")

            # ── Output Validation：AI 輸出合理性驗證 ─────────────────────────
            _val_err = _validate_output(updated_data, intent, session, user_id, current_context)
            if _val_err:
                return ChatResponse(
                    ai_reply=_val_err,
                    updated_data=updated_data,
                    is_complete=False,
                )

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
                    end_time = start_time.replace(hour=min(start_time.hour + 2, 23))
            else:
                # edit without time change — will be filled from existing record
                start_time = None
                end_time = None

            location_name = updated_data.get("location")
            location_lat = None
            location_lon = None

            # Define effective_schedule_id early — needed inside location block too
            effective_schedule_id = request.schedule_id or (target_schedule_id if intent == "edit" else None)

            # ── Pre-compute owned schedule IDs (edit intent only) ─────────────
            # Used to restrict fuzzy recovery to schedules the user can actually edit.
            # Attendee-only schedules are intentionally excluded.
            _owned_schedule_ids: set = set()
            if intent == "edit":
                from sqlmodel import select as _sel
                _owned_schedule_ids = set(
                    session.exec(_sel(Schedule.schedule_id).where(Schedule.user_id == current_user.user_id)).all()
                )

            # ── Early schedule validation for edit intent ─────────────────────
            # Validate the target schedule exists AND is owned by current user
            # BEFORE location search, so hallucinated/wrong IDs are caught early.
            if intent == "edit" and effective_schedule_id:
                _repo_early = ScheduleRepository(session)
                _early_existing = _repo_early.get_by_schedule_id(effective_schedule_id)
                # Reject if not found OR owned by a different user (user is only attendee)
                if _early_existing is None or effective_schedule_id not in _owned_schedule_ids:
                    if _early_existing is not None and effective_schedule_id not in _owned_schedule_ids:
                        # Schedule exists but user is only an attendee — no fuzzy needed,
                        # but we still check owned schedules for a better match
                        print(f"[chat edit] attendee-only schedule rejected: {effective_schedule_id}, "
                              f"owner={_early_existing.user_id}, current={current_user.user_id}")
                        try:
                            from ...services.constraint_store import record_error as _rc
                            _rc("attendee_only_schedule",
                                example=f"AI picked schedule_id={effective_schedule_id!r} owned by {_early_existing.user_id!r}")
                        except Exception:
                            pass
                    # Fuzzy recovery — restricted to OWNED schedules only
                    _fe_ids = {
                        s.get("schedule_id") or s.get("id", "")
                        for s in (annotated_schedule_list or [])
                    } & _owned_schedule_ids
                    _fe_best, _fe_sim = None, 0.0
                    for _fe_sid in _fe_ids:
                        if (_fe_sid and len(_fe_sid) == len(effective_schedule_id)
                                and _fe_sid[:4] == effective_schedule_id[:4]):
                            _sim = sum(a == b for a, b in zip(effective_schedule_id, _fe_sid)) / len(_fe_sid)
                            if _sim > _fe_sim:
                                _fe_sim, _fe_best = _sim, _fe_sid
                    if _fe_best and _fe_sim >= 0.92:
                        print(f"[chat edit] early fuzzy-recovery: {effective_schedule_id} → {_fe_best} (sim={_fe_sim:.2f})")
                        effective_schedule_id = _fe_best
                        target_schedule_id = _fe_best
                    elif _early_existing is not None and effective_schedule_id not in _owned_schedule_ids:
                        # Attendee-only, no owned alternative found — list owned schedules
                        _owned_list = [s for s in (annotated_schedule_list or [])
                                       if (s.get("schedule_id") or s.get("id", "")) in _owned_schedule_ids]
                        _msg = _build_schedule_list_reply(
                            f"「{_early_existing.title}」是由其他人建立的行程，您以參與者身分加入，無法修改。\n請問您想修改哪個行程呢？",
                            _owned_list or annotated_schedule_list or [],
                        )
                        return ChatResponse(ai_reply=_msg, updated_data={}, is_complete=False)
                    else:
                        _msg = _build_schedule_list_reply(
                            "找不到符合描述的行程，請問是哪個行程需要更改？",
                            annotated_schedule_list or [],
                        )
                        return ChatResponse(ai_reply=_msg, updated_data={}, is_complete=False)

            if location_name:
                # If coords already confirmed (confirm_location or explicit lat/lon), use them directly
                ctx_lat = updated_data.get("latitude") or updated_data.get("lat")
                ctx_lon = updated_data.get("longitude") or updated_data.get("lon")
                if ctx_lat and ctx_lon:
                    location_lat = float(ctx_lat)
                    location_lon = float(ctx_lon)
                elif request.confirm_location and request.latitude and request.longitude:
                    location_lat = request.latitude
                    location_lon = request.longitude
                else:
                    # Create / Edit 都走 validate_location 顯示候選地點
                    # 加 15 秒總 timeout，避免 4-layer HERE 最壞 38s 超過 Flutter 40s 限制
                    import concurrent.futures as _cf
                    _loc_result = None
                    try:
                        with _cf.ThreadPoolExecutor(max_workers=1) as _ex:
                            _fut = _ex.submit(
                                HereService.validate_location,
                                location_name,
                                lat=request.latitude,
                                lon=request.longitude,
                            )
                            _loc_result = _fut.result(timeout=15)
                    except _cf.TimeoutError:
                        print(f"[location] validate_location timeout for '{location_name}'")
                    except Exception as _loc_err:
                        print(f"[location] validate_location error: {_loc_err}")

                    if _loc_result is None:
                        # HERE timeout 或失敗：edit 直接儲存地點名稱，create 則提示
                        if intent != "edit":
                            return ChatResponse(
                                ai_reply=f"地點搜尋逾時，請稍後再試或提供更詳細的地址。",
                                updated_data=updated_data,
                                is_complete=False,
                            )
                        # edit 逾時：地點名稱已存，座標之後補
                    elif _loc_result["needs_selection"] or (_loc_result["best"] is None):
                        candidates_clean = [
                            {
                                "name": c.get("name") or c.get("address", "").split(",")[0].strip() or f"地點 {i+1}",
                                "address": c.get("address", ""),
                                "lat": c["lat"],
                                "lon": c["lon"],
                            }
                            for i, c in enumerate(_loc_result.get("candidates", []))
                            if c.get("name") or c.get("address")
                        ]
                        # effective_schedule_id already validated by early-check above
                        edit_ctx = dict(updated_data)
                        edit_ctx["_pending_edit_schedule_id"] = effective_schedule_id or target_schedule_id
                        if len(candidates_clean) == 1:
                            # Single result: show confirm card, not selection list
                            single = candidates_clean[0]
                            return ChatResponse(
                                ai_reply=f"我為您找到了「{single['name']}」（{single['address']}）。請問這個地點正確嗎？",
                                updated_data=edit_ctx,
                                is_complete=False,
                                needs_location_confirm=True,
                                location_details=single,
                            )
                        elif candidates_clean:
                            return ChatResponse(
                                ai_reply=f"我找到了幾個「{location_name}」，請選擇正確的地點：",
                                updated_data=edit_ctx,
                                is_complete=False,
                                needs_location_confirm=True,
                                location_candidates=candidates_clean,
                            )
                        else:
                            return ChatResponse(
                                ai_reply=f"找不到「{location_name}」，請直接輸入完整地址或更換地點名稱。",
                                updated_data=updated_data,
                                is_complete=False,
                                location_not_found=True,
                            )
                    elif _loc_result["best"]:
                        best = _loc_result["best"]
                        location_lat = best["lat"]
                        location_lon = best["lon"]

            repo = ScheduleRepository(session)

            # 3. 檢查衝突 (Conflict Detection — only for create, skip for edit)
            if not request.force_create and intent != "edit" and start_time:
                conflicts = repo.find_overlapping(current_user.user_id, start_time, end_time)
                if conflicts:
                    # Found conflicts (could be multiple)
                    conflict_details = []
                    for c in conflicts:
                        from ...services.chat_utils import _to_taipei as _ttp
                        p_start = _ttp(c.meeting_start_time).format('HH:mm')
                        p_end = _ttp(c.meeting_end_time).format('HH:mm') if c.meeting_end_time else "??"
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
                            "end_time": base_conflict.meeting_end_time.isoformat() if isinstance(base_conflict.meeting_end_time, datetime) else str(base_conflict.meeting_end_time) if base_conflict.meeting_end_time else None
                        }
                    )

            # ── Update existing schedule (chat edit intent or correction) ──────
            if effective_schedule_id:
                # Guard：沒有任何欄位需要更新 → 不執行空更新，回問用戶
                _edit_parts = updated_data.get("participants", [])
                if isinstance(_edit_parts, str):
                    _edit_parts = [p.strip() for p in _edit_parts.split(",") if p.strip()]
                _remove_parts = updated_data.get("remove_participants", [])
                if isinstance(_remove_parts, str):
                    _remove_parts = [p.strip() for p in _remove_parts.split(",") if p.strip()]
                _clear_parts = bool(updated_data.get("clear_participants"))
                has_changes = (
                    updated_data.get("title") or
                    updated_data.get("description") or
                    updated_data.get("start_time") or
                    location_name or
                    _edit_parts or
                    _remove_parts or
                    _clear_parts
                )
                if not has_changes:
                    return ChatResponse(
                        ai_reply="請問您想把哪些內容改成什麼呢？（例如：改成下午五點、地點換到星巴克）",
                        updated_data=updated_data,
                        is_complete=False,
                    )

                existing = repo.get_by_schedule_id(effective_schedule_id)

                # If not found, attempt fuzzy recovery — non-Cerebras models sometimes
                # hallucinate 1-3 chars in a long ID (confirmed from Groq logs).
                # This also fixes confirm_location flows where _pending_edit_schedule_id
                # was set from a previously hallucinated target_schedule_id.
                if existing is None and effective_schedule_id and annotated_schedule_list:
                    _fr_ids = {
                        s.get("schedule_id") or s.get("id", "")
                        for s in annotated_schedule_list
                    }
                    _fr_best, _fr_sim = None, 0.0
                    for _fr_sid in _fr_ids:
                        if _fr_sid and len(_fr_sid) == len(effective_schedule_id) and _fr_sid[:4] == effective_schedule_id[:4]:
                            _sim = sum(a == b for a, b in zip(effective_schedule_id, _fr_sid)) / len(_fr_sid)
                            if _sim > _fr_sim:
                                _fr_sim, _fr_best = _sim, _fr_sid
                    if _fr_best and _fr_sim >= 0.92:
                        print(f"[chat edit] fuzzy-recovery (existing=None): "
                              f"{effective_schedule_id} → {_fr_best} (sim={_fr_sim:.2f})")
                        effective_schedule_id = _fr_best
                        target_schedule_id = _fr_best
                        existing = repo.get_by_schedule_id(effective_schedule_id)

                # 驗證 AI 選的行程確實和用戶描述的人名/關鍵字吻合
                # 避免 AI 語意搜尋誤匹配到不相關行程
                if existing and existing.user_id == current_user.user_id:
                    _keyword_hint = user_message  # 用原始訊息做關鍵字驗證
                    _stop = {"更改", "修改", "調整", "更新", "改", "把", "的", "時間",
                             "地點", "行程", "活動", "我要", "請", "幫我", "到", "改成"}
                    _kw_chars = [c for c in _keyword_hint if c not in _stop and len(c.strip()) > 0]
                    _kw = "".join(_kw_chars)
                    # 只在有關鍵字且清單非空時才驗證（避免誤擋正常流程）
                    # Skip keyword validation for confirm_location: message is "Confirm", not a schedule description
                    # Skip if already validated as owned by early check (owned = already verified)
                    _schedule_ids_in_list = {
                        s.get("schedule_id") or s.get("id", "")
                        for s in (annotated_schedule_list or [])
                    }
                    _id_was_in_list = (
                        effective_schedule_id in _owned_schedule_ids  # early check already confirmed ownership
                        or effective_schedule_id in _schedule_ids_in_list
                    )
                    if not _id_was_in_list and annotated_schedule_list and not request.confirm_location:
                        # Non-Cerebras models sometimes hallucinate 1-3 chars in a long ID.
                        # Fuzzy recovery searches owned IDs only (not attended-only ones).
                        _fuzzy_pool = (_owned_schedule_ids & _schedule_ids_in_list) if _owned_schedule_ids else _schedule_ids_in_list
                        _best_fuzzy, _best_sim = None, 0.0
                        for _sid in _fuzzy_pool:
                            if _sid and len(_sid) == len(effective_schedule_id) and _sid[:4] == effective_schedule_id[:4]:
                                _sim = sum(a == b for a, b in zip(effective_schedule_id, _sid)) / len(_sid)
                                if _sim > _best_sim:
                                    _best_sim, _best_fuzzy = _sim, _sid
                        if _best_fuzzy and _best_sim >= 0.92:
                            print(f"[chat edit] fuzzy-recovered schedule_id: "
                                  f"{effective_schedule_id} → {_best_fuzzy} (sim={_best_sim:.2f})")
                            effective_schedule_id = _best_fuzzy
                            target_schedule_id = _best_fuzzy
                        else:
                            print(f"[chat edit] WARNING: schedule_id={effective_schedule_id} "
                                  f"not in annotated_schedule_list, possible mismatch")
                            try:
                                from ...services.constraint_store import record_error as _rc
                                _rc("wrong_schedule_id",
                                    example=f"AI returned schedule_id={effective_schedule_id!r} not in list")
                            except Exception:
                                pass
                            _owned_list2 = [s for s in (annotated_schedule_list or [])
                                            if (s.get("schedule_id") or s.get("id", "")) in _owned_schedule_ids]
                            _msg2 = _build_schedule_list_reply(
                                "找不到符合描述的行程，請問是哪個行程需要更改？",
                                _owned_list2 or annotated_schedule_list or [],
                            )
                            return ChatResponse(ai_reply=_msg2, updated_data={}, is_complete=False)
                if existing and existing.user_id == current_user.user_id:
                    # ── Past-schedule guard ───────────────────────────────────
                    from datetime import timezone as _tz, timedelta as _td
                    _taipei_now = datetime.now(tz=_tz(_td(hours=8)))
                    _s_time = existing.meeting_start_time
                    if isinstance(_s_time, str):
                        try:
                            _s_time = datetime.fromisoformat(_s_time.replace("Z", "+00:00"))
                        except Exception:
                            _s_time = None
                    if _s_time:
                        _s_aware = _s_time.replace(tzinfo=_tz(_td(hours=8))) if _s_time.tzinfo is None else _s_time
                        if _s_aware < _taipei_now and not request.confirm_past_edit:
                            _past_info = {
                                "id": existing.schedule_id,
                                "title": existing.title,
                                "start_time": _s_time.isoformat() if isinstance(_s_time, datetime) else str(_s_time),
                            }
                            from ...services.chat_utils import _to_taipei, _display_hour
                            _t = _to_taipei(_s_time)
                            _h = _t.hour
                            _p = "上午" if 6 <= _h < 12 else "中午" if 12 <= _h < 14 else "下午" if 14 <= _h < 18 else "晚上" if 18 <= _h < 22 else "深夜"
                            _past_str = f"{_t.month}月{_t.day}日 {_p}{_display_hour(_h)}點"
                            # 儲存至 context，讓用戶下一則訊息自動確認（不必再點按鈕）
                            _warn_data = dict(updated_data)
                            _warn_data["_pending_past_edit_id"] = existing.schedule_id
                            # Preserve validated coords so confirm_past_edit bypass skips re-validation
                            if location_lat:
                                _warn_data["latitude"] = location_lat
                            if location_lon:
                                _warn_data["longitude"] = location_lon
                            return ChatResponse(
                                ai_reply=f"「{existing.title}」是 {_past_str} 的行程，已經過去了，確定要修改嗎？",
                                updated_data=_warn_data,
                                is_complete=False,
                                confirm_past_edit=_past_info,
                            )
                    # Only update fields that were explicitly provided in updated_data
                    if updated_data.get("title"): existing.title = updated_data["title"]
                    if updated_data.get("description"): existing.description = updated_data["description"]
                    if updated_data.get("start_time"):
                        existing.meeting_start_time = start_time
                        existing.meeting_end_time = end_time
                        # Reset NA/CS status when rescheduled to future
                        if existing.status in {Status.COMING_SOON.value, "NA"} and start_time:
                            try:
                                from ...services.chat_utils import _to_taipei as _ttp3
                                _new_tw = _ttp3(start_time)
                                if _new_tw and _new_tw > arrow.now("Asia/Taipei").shift(hours=3):
                                    existing.status = Status.PENDING.value
                            except Exception:
                                pass
                    if location_name:
                        existing.meeting_location = location_name
                        existing.location = location_name
                        # 座標已在 edit 模式的 quick geocode 處理，這裡直接使用
                    if location_lat and location_lon:
                        existing.latitude = location_lat
                        existing.longitude = location_lon
                    saved_schedule_obj = repo.update(existing)
                    saved_schedule = saved_schedule_obj.dict()
                    # ── 新增 / 移除參與者 ────────────────────────────────────────
                    if _clear_parts:
                        from sqlmodel import delete as _sql_del
                        from ...models.attend import attend as _attend_clr
                        session.exec(_sql_del(_attend_clr).where(_attend_clr.schedule_id == saved_schedule_obj.schedule_id))
                        session.commit()
                    elif _edit_parts:
                        _add_participants(saved_schedule_obj.schedule_id, _edit_parts,
                                          current_user.user_id, session)
                    if not _clear_parts and _remove_parts:
                        _remove_participants(saved_schedule_obj.schedule_id, _remove_parts,
                                             current_user.user_id, session)
                    _summary = _fmt_schedule_summary(saved_schedule_obj)
                    _change_lines = []
                    if _clear_parts:
                        _change_lines.append("➖ 已移除所有參與者（個人行程）")
                    elif _edit_parts:
                        _names = " ".join(f"@{p.strip().lstrip('@')}" for p in _edit_parts if p.strip())
                        _change_lines.append(f"➕ 新增參與者：{_names}")
                    if not _clear_parts and _remove_parts:
                        _rnames = " ".join(f"@{p.strip().lstrip('@')}" for p in _remove_parts if p.strip())
                        _change_lines.append(f"➖ 移除參與者：{_rnames}")
                    if _change_lines:
                        _summary += "\n" + "\n".join(_change_lines)
                    ai_reply = f"✅ 已為您更新行程！\n{_summary}"
                    print(f"DEBUG [chat]: Schedule updated ID={effective_schedule_id}")
                    # 更新 embedding（豐富化：加入聯絡人姓名 + 時間語境）
                    try:
                        from ...services.embedding_service import EmbeddingService
                        from ...models.contact import Contact as _Contact
                        _cname = ""
                        if existing.contact_id:
                            _c = session.get(_Contact, existing.contact_id)
                            if _c:
                                _cname = _c.nick_name or ""
                        emb = EmbeddingService.embed_schedule(
                            existing.title or "",
                            existing.meeting_location or "",
                            existing.description or "",
                            contact_name=_cname,
                            start_time=existing.meeting_start_time,
                        )
                        repo.upsert_embedding(existing.schedule_id, emb)
                    except Exception as _emb_err:
                        print(f"[embedding] update failed (non-critical): {_emb_err}")
                        try:
                            session.rollback()
                        except Exception:
                            pass
                    # 記憶學習（背景，失敗不影響主流程）
                    try:
                        from ...services.memory_service import MemoryService
                        MemoryService.extract_and_save(
                            user_id, saved_schedule, "edit", _cname, session
                        )
                    except Exception:
                        pass
                else:
                    print(f"[chat edit] ownership check failed: "
                          f"effective_schedule_id={effective_schedule_id}, "
                          f"existing={'None' if existing is None else f'owner={existing.user_id}'}, "
                          f"current_user={current_user.user_id}")
                    _owned_list3 = [s for s in (annotated_schedule_list or [])
                                    if (s.get("schedule_id") or s.get("id", "")) in _owned_schedule_ids]
                    if existing is not None:
                        _msg3 = _build_schedule_list_reply(
                            f"「{existing.title}」是由其他人建立的行程，您以參與者身分加入，無法修改。\n請問您想修改哪個行程呢？",
                            _owned_list3 or annotated_schedule_list or [],
                        )
                    else:
                        _msg3 = _build_schedule_list_reply(
                            "找不到符合描述的行程，請問是哪個行程需要更改？",
                            _owned_list3 or annotated_schedule_list or [],
                        )
                    return ChatResponse(ai_reply=_msg3, updated_data={}, is_complete=False)
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
                ai_reply = f"✅ 已為您建立行程！\n{_fmt_schedule_summary(saved_schedule_obj)}"
                # 產生 embedding（豐富化：加入聯絡人 + 時間語境）
                _new_cname = ""
                try:
                    from ...services.embedding_service import EmbeddingService
                    # 嘗試從 participants 取聯絡人名
                    _parts = updated_data.get("participants", [])
                    if isinstance(_parts, list) and _parts:
                        _new_cname = _parts[0].strip().lstrip("@")
                    elif isinstance(_parts, str) and _parts:
                        _new_cname = _parts.split(",")[0].strip().lstrip("@")
                    emb = EmbeddingService.embed_schedule(
                        updated_data.get("title", ""),
                        location_name or "",
                        updated_data.get("description", ""),
                        contact_name=_new_cname,
                        start_time=start_time,
                    )
                    repo.upsert_embedding(saved_schedule_obj.schedule_id, emb)
                except Exception as _emb_err:
                    print(f"[embedding] create failed (non-critical): {_emb_err}")
                    try:
                        session.rollback()
                    except Exception:
                        pass
                # 記憶學習（背景）
                try:
                    from ...services.memory_service import MemoryService
                    MemoryService.extract_and_save(
                        user_id, saved_schedule, "create", _new_cname, session
                    )
                except Exception:
                    pass
            
            # 如果有參與者，這邊處理 attend 表（僅 create；edit 已由 _edit_parts 處理）
            participants = updated_data.get("participants", [])
            # Handle cases where participants might be a string
            if isinstance(participants, str):
                 participants = [p.strip() for p in participants.split(",")]

            if intent != "edit" and participants and isinstance(participants, list):
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
            print(f"Error {'updating' if intent == 'edit' else 'creating'} schedule: {e}")
            import traceback
            traceback.print_exc()
            action_word = "更新" if intent == "edit" else "建立"
            return ChatResponse(
                ai_reply=f"行程{action_word}失敗，請稍後再試。",
                updated_data=updated_data,
                is_complete=False  # 失敗時不清除 context，讓用戶可以重試
            )

    # 3. 儲存對話紀錄到 Redis（confirm_location / confirm_delete 不重複記錄）
    if not request.confirm_location and not request.confirm_delete and not request.confirm_past_edit and ai_reply:
        redis_client.append_chat_turn(user_id, user_message, ai_reply)

    # 若對話完成或刪除，清除 context；否則更新 context
    if is_complete or getattr(request, 'schedule_deleted', False):
        redis_client.clear_chat_context(user_id)
    elif updated_data:
        redis_client.set_chat_context(user_id, updated_data)

    # 4. 回傳結果
    # 任何 intent 完成後都回傳空 context，讓 Flutter 清除 _currentContext 並刷新清單
    return_data = {} if is_complete else updated_data
    return ChatResponse(
        ai_reply=ai_reply,
        updated_data=return_data,
        is_complete=is_complete,
        schedule=saved_schedule
    )


@router.post("/chat/feedback", response_model=dict)
def submit_feedback(
    req: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    fb = AIFeedback(
        user_id=current_user.user_id,
        user_message=req.user_message,
        ai_reply=req.ai_reply,
        is_good=req.is_good,
        correction=req.correction,
        conversation_json=req.conversation_json,
        model_label=req.model_label,
    )
    session.add(fb)
    session.commit()

    # 👎 feedback → auto-record as unknown error pattern so it's flagged for review
    if not req.is_good:
        try:
            from ...services.constraint_store import record_error as _rc
            _rc(
                "user_thumbs_down",
                example=f"user={req.user_message[:80]!r} ai={req.ai_reply[:80]!r}",
                custom_constraint=(
                    f"以下類型的回覆曾被用戶標記為錯誤，請避免類似模式："
                    f"「{req.ai_reply[:60]}」"
                    + (f"（用戶更正：{req.correction[:60]}）" if req.correction else "")
                ),
            )
        except Exception:
            pass

    return {"ok": True}