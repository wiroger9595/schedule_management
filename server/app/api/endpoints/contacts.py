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
def get_contacts(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = ContactRepository(session)
    return repo.get_all_by_user(current_user.user_id)

@router.post("/", response_model=Contact)
def create_contact(contact_data: dict, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = ContactRepository(session)
    
    name = contact_data.get("name")
    phone = contact_data.get("phone")
    if not name or not phone:
        raise HTTPException(status_code=400, detail="Name and phone required")
        
    contact = Contact(
        user_id=current_user.user_id,
        name=name,
        phone=phone
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
