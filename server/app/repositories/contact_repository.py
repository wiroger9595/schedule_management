from typing import List, Optional
from sqlmodel import Session, select
from sqlalchemy.orm import aliased
from ..models.contact import Contact
from ..models.user import User
from ..schemas.contact import ContactRead

class ContactRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all_by_user(self, user_id: str) -> List[ContactRead]:
        # Perform a left join to get the linked user's profile image
        statement = (
            select(Contact, User.profile_image_path)
            .outerjoin(User, Contact.contact_user_id == User.user_id)
            .where(Contact.user_id == user_id)
        )
        results = self.session.exec(statement).all()
        
        # Map to ContactRead
        contacts = []
        for contact, profile_image_path in results:
            contact_read = ContactRead.model_validate(contact)
            contact_read.profile_image_path = profile_image_path
            contacts.append(contact_read)
            
        return contacts

    def get_by_id(self, contact_id: int) -> Optional[Contact]:
        return self.session.get(Contact, contact_id)

    def create(self, contact: Contact) -> Contact:
        self.session.add(contact)
        self.session.commit()
        self.session.refresh(contact)
        return contact
        
    def delete(self, contact: Contact) -> None:
        self.session.delete(contact)
        self.session.commit()

    def update(self, contact: Contact) -> Contact:
        self.session.add(contact)
        self.session.commit()
        self.session.refresh(contact)
        return contact

    def check_duplicate(self, user_id: str, phone: Optional[str] = None, email: Optional[str] = None, line_id: Optional[str] = None, exclude_contact_id: Optional[int] = None) -> Optional[str]:
        if phone:
            stmt = select(Contact).where(Contact.user_id == user_id, Contact.phone == phone)
            if exclude_contact_id:
                stmt = stmt.where(Contact.id != exclude_contact_id)
            if self.session.exec(stmt).first():
                return "phone"
        if email:
            stmt = select(Contact).where(Contact.user_id == user_id, Contact.email == email)
            if exclude_contact_id:
                stmt = stmt.where(Contact.id != exclude_contact_id)
            if self.session.exec(stmt).first():
                return "email"
        if line_id:
            stmt = select(Contact).where(Contact.user_id == user_id, Contact.line_id == line_id)
            if exclude_contact_id:
                stmt = stmt.where(Contact.id != exclude_contact_id)
            if self.session.exec(stmt).first():
                return "line"
        return None
