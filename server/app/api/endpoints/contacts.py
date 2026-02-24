from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
from ...db.database import get_session
from ...models.contact import Contact
from ...models.user import User
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

@router.post("/validate", response_model=ContactValidateResponse)
def validate_contact(
    request: ContactValidateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
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
    repo = ContactRepository(session)
    contact = repo.get_by_id(contact_id)
    if not contact or contact.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Contact not found")
        
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
        
    # Update fields if present, mapping empty strings to None
    if contact_data.nick_name is not None: contact.nick_name = contact_data.nick_name
    if contact_data.phone is not None: contact.phone = contact_data.phone if contact_data.phone else None
    if contact_data.email is not None: contact.email = contact_data.email if contact_data.email else None
    if contact_data.line_id is not None: contact.line_id = contact_data.line_id if contact_data.line_id else None
    if contact_data.comment is not None: contact.comment = contact_data.comment if contact_data.comment else None
    if contact_data.contact_user_id is not None: contact.contact_user_id = contact_data.contact_user_id if contact_data.contact_user_id else None
    
    duplicate = repo.check_duplicate(
        user_id=current_user.user_id,
        phone=contact.phone,
        email=contact.email,
        line_id=contact.line_id,
        exclude_contact_id=contact.id
    )
    if duplicate == "phone":
        raise HTTPException(status_code=400, detail="有重複的電話號碼")
    elif duplicate == "email":
        raise HTTPException(status_code=400, detail="有重複的email")
    elif duplicate == "line":
        raise HTTPException(status_code=400, detail="有重複的line")

    return repo.update(contact)
