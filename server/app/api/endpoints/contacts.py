from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
from ...db.database import get_session
from ...models.contact import Contact
from ...models.user import User
from ...repositories.contact_repository import ContactRepository
from .auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[Contact])
@router.get("", response_model=List[Contact], include_in_schema=False)
def get_contacts(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = ContactRepository(session)
    return repo.get_all_by_user(current_user.user_id)

@router.post("/", response_model=Contact)
@router.post("", response_model=Contact, include_in_schema=False)
def create_contact(contact_data: dict, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = ContactRepository(session)
    
    # Extract fields
    neck_name = contact_data.get("neck_name") or contact_data.get("name")
    phone = contact_data.get("phone")
    email = contact_data.get("email")
    line_id = contact_data.get("line_id")
    contact_user_id = contact_data.get("contact_user_id")
    comment = contact_data.get("comment")

    # Basic validation (optional)
    if not neck_name and not phone and not email and not line_id:
         raise HTTPException(status_code=400, detail="At least one contact detail (name, phone, email, line_id) is required")
        
    contact = Contact(
        user_id=current_user.user_id,
        contact_user_id=contact_user_id,
        neck_name=neck_name,
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
    contact_data: dict, 
    current_user: User = Depends(get_current_user), 
    session: Session = Depends(get_session)
):
    repo = ContactRepository(session)
    contact = repo.get_by_id(contact_id)
    
    if not contact or contact.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Contact not found")
        
    # Update fields if present
    if "neck_name" in contact_data: contact.neck_name = contact_data["neck_name"]
    if "phone" in contact_data: contact.phone = contact_data["phone"]
    if "email" in contact_data: contact.email = contact_data["email"]
    if "line_id" in contact_data: contact.line_id = contact_data["line_id"]
    if "comment" in contact_data: contact.comment = contact_data["comment"]
    if "contact_user_id" in contact_data: contact.contact_user_id = contact_data["contact_user_id"]
    
    return repo.update(contact)
