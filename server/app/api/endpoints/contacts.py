from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from ...db.database import get_session
from ...models.contact import Contact
from ...models.user import User
from ...repositories.contact_repository import ContactRepository
from ...repositories.schedule_repository import ScheduleRepository
from ...schemas.contact import ContactCreate, ContactUpdate, ContactRead, ContactValidateRequest, ContactValidateResponse
from .auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[ContactRead])
@router.get("", response_model=List[ContactRead], include_in_schema=False)
def get_contacts(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = ContactRepository(session)
    return repo.get_all_by_user(current_user.user_id)

@router.get("/{contact_id}/schedules", response_model=List[dict])
def get_contact_schedules(contact_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """
    Get all schedules where this contact (or their linked user) is a participant.
    """
    repo = ScheduleRepository(session)
    schedules = repo.get_schedules_with_contact(current_user.user_id, contact_id)
    return [s.dict() for s in schedules]

@router.get("/check-email")
def check_email_user(
    email: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    查詢某個 email 是否是已註冊的用戶（排除自己）。
    回傳 found=True 時附上 user_id / full_name。
    """
    from sqlmodel import select
    user = session.exec(select(User).where(User.email == email)).first()
    if user and user.user_id != current_user.user_id:
        return {"found": True, "user_id": user.user_id, "full_name": user.full_name, "email": user.email}
    return {"found": False}


@router.post("/validate", response_model=ContactValidateResponse)
def validate_contact(
    request: ContactValidateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Check self
    if request.email and request.email == current_user.email:
        return ContactValidateResponse(is_valid=False, duplicate_field="self_email")
    if request.phone and current_user.phone and request.phone == current_user.phone:
        return ContactValidateResponse(is_valid=False, duplicate_field="self_phone")

    repo = ContactRepository(session)
    duplicate = repo.check_duplicate(
        user_id=current_user.user_id,
        phone=request.phone if request.phone else None,
        email=request.email if request.email else None,
        line_id=request.line_id if request.line_id else None,
        exclude_contact_id=request.exclude_contact_id
    )

    if duplicate:
        return ContactValidateResponse(is_valid=False, duplicate_field=duplicate)

    return ContactValidateResponse(is_valid=True, duplicate_field=None)

@router.post("/", response_model=Contact)
@router.post("", response_model=Contact, include_in_schema=False)
def create_contact(contact_data: ContactCreate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = ContactRepository(session)
    
    # Extract fields and treat empty strings as None to avoid unique constraint matching
    nick_name = contact_data.nick_name or contact_data.name
    phone = contact_data.phone if contact_data.phone else None
    email = contact_data.email if contact_data.email else None
    line_id = contact_data.line_id if contact_data.line_id else None
    contact_user_id = contact_data.contact_user_id if contact_data.contact_user_id else None
    comment = contact_data.comment if contact_data.comment else None

    # Basic validation (optional)
    if not nick_name and not phone and not email and not line_id:
         raise HTTPException(status_code=400, detail="At least one contact detail (name, phone, email, line_id) is required")

    # Cannot add yourself
    if email and email == current_user.email:
        raise HTTPException(status_code=400, detail="不能將自己加為聯絡人")
    if phone and current_user.phone and phone == current_user.phone:
        raise HTTPException(status_code=400, detail="不能將自己加為聯絡人")

    # Auto-link to app user if email matches
    if not contact_user_id and email:
        matched_user = session.exec(select(User).where(User.email == email)).first()
        if matched_user and matched_user.user_id != current_user.user_id:
            contact_user_id = matched_user.user_id
        
    duplicate = repo.check_duplicate(
        user_id=current_user.user_id,
        phone=phone,
        email=email,
        line_id=line_id
    )
    if duplicate == "phone":
        raise HTTPException(status_code=400, detail="有重複的電話號碼")
    elif duplicate == "email":
        raise HTTPException(status_code=400, detail="有重複的email")
    elif duplicate == "line":
        raise HTTPException(status_code=400, detail="有重複的line")

    contact = Contact(
        user_id=current_user.user_id,
        contact_user_id=contact_user_id,
        nick_name=nick_name,
        phone=phone,
        email=email,
        line_id=line_id,
        comment=comment
    )
    return repo.create(contact)

@router.delete("/{contact_id}")
def delete_contact(contact_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    from ...models.attend import attend as Attend
    from ...models.schedule import Schedule
    from sqlalchemy import delete as sa_delete

    repo = ContactRepository(session)
    contact = repo.get_by_id(contact_id)
    if not contact or contact.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Phase 1: collect all schedule_ids related to this contact
    direct_schedule_ids = {
        s.schedule_id for s in session.exec(
            select(Schedule).where(
                Schedule.user_id == current_user.user_id,
                Schedule.contact_id == contact_id
            )
        ).all()
    }
    attendee_schedule_ids = {
        a.schedule_id for a in session.exec(
            select(Attend).where(Attend.contact_id == contact_id)
        ).all()
    }
    all_schedule_ids = list(direct_schedule_ids | attendee_schedule_ids)

    # Phase 2: bulk-delete attend records (bypasses ORM cascade/relationship issues)
    if all_schedule_ids:
        session.execute(
            sa_delete(Attend).where(Attend.schedule_id.in_(all_schedule_ids)),
            execution_options={"synchronize_session": "fetch"},
        )
    session.execute(
        sa_delete(Attend).where(Attend.contact_id == contact_id),
        execution_options={"synchronize_session": "fetch"},
    )

    # Phase 3: bulk-delete schedules
    if all_schedule_ids:
        session.execute(
            sa_delete(Schedule).where(Schedule.schedule_id.in_(all_schedule_ids)),
            execution_options={"synchronize_session": "fetch"},
        )

    session.flush()
    repo.delete(contact)
    return {"msg": "Deleted"}

@router.put("/{contact_id}", response_model=Contact)
@router.put("/{contact_id}/", response_model=Contact, include_in_schema=False)
def update_contact(
    contact_id: int,
    contact_data: ContactUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    repo = ContactRepository(session)
    contact = repo.get_by_id(contact_id)

    if not contact or contact.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Compute the effective values BEFORE touching the ORM object so that
    # check_duplicate doesn't trigger an autoflush on a dirty instance.
    effective_phone   = (contact_data.phone   if contact_data.phone   else None) if contact_data.phone   is not None else contact.phone
    effective_email   = (contact_data.email   if contact_data.email   else None) if contact_data.email   is not None else contact.email
    effective_line_id = (contact_data.line_id if contact_data.line_id else None) if contact_data.line_id is not None else contact.line_id

    duplicate = repo.check_duplicate(
        user_id=current_user.user_id,
        phone=effective_phone,
        email=effective_email,
        line_id=effective_line_id,
        exclude_contact_id=contact.id
    )
    if duplicate == "phone":
        raise HTTPException(status_code=400, detail="有重複的電話號碼")
    elif duplicate == "email":
        raise HTTPException(status_code=400, detail="有重複的email")
    elif duplicate == "line":
        raise HTTPException(status_code=400, detail="有重複的line")

    # Now it's safe to modify the ORM object
    if contact_data.nick_name is not None: contact.nick_name = contact_data.nick_name
    if contact_data.phone is not None: contact.phone = effective_phone
    if contact_data.email is not None: contact.email = effective_email
    if contact_data.line_id is not None: contact.line_id = effective_line_id
    if contact_data.comment is not None: contact.comment = contact_data.comment if contact_data.comment else None
    if contact_data.contact_user_id is not None: contact.contact_user_id = contact_data.contact_user_id if contact_data.contact_user_id else None

    return repo.update(contact)
