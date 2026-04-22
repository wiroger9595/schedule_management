from sqlmodel import select

from ..models.contact import Contact
from ..models.attend import attend


def add_participants(schedule_id: str, names: list, user_id: str, session) -> list:
    """Add participants by name. Creates contact if not found. Returns list of added clean names."""
    added = []
    for pname in names:
        clean = pname.strip().lstrip("@")
        if not clean:
            continue
        contact = session.exec(
            select(Contact).where(Contact.user_id == user_id, Contact.nick_name == clean)
        ).first()
        if not contact:
            contact = Contact(user_id=user_id, nick_name=clean)
            session.add(contact)
            session.commit()
            session.refresh(contact)
        exists = session.exec(
            select(attend).where(attend.schedule_id == schedule_id, attend.contact_id == contact.id)
        ).first()
        if not exists:
            session.add(attend(schedule_id=schedule_id, contact_id=contact.id, status="P"))
            added.append(clean)
    session.commit()
    return added


def remove_participants(schedule_id: str, names: list, user_id: str, session) -> list:
    """Remove participants by name. Returns list of removed clean names."""
    removed = []
    for pname in names:
        clean = pname.strip().lstrip("@")
        if not clean:
            continue
        contact = session.exec(
            select(Contact).where(Contact.user_id == user_id, Contact.nick_name == clean)
        ).first()
        if contact:
            att = session.exec(
                select(attend).where(attend.schedule_id == schedule_id, attend.contact_id == contact.id)
            ).first()
            if att:
                session.delete(att)
                removed.append(clean)
    session.commit()
    return removed
