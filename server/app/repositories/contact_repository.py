from typing import List, Optional
from sqlmodel import Session, select
from ..models.contact import Contact

class ContactRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all_by_user(self, user_id: str) -> List[Contact]:
        return self.session.exec(select(Contact).where(Contact.user_id == user_id)).all()

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
