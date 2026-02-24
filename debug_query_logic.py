
import sys
import os
from sqlmodel import Session, select, or_

sys.path.append(os.path.join(os.getcwd(), 'server'))

from app.db.database import engine
from app.models.schedule import Schedule
from app.models.attend import attend
from app.models.contact import Contact
from app.models.user import User

def debug_query():
    user_id = 'ur68bc611c4fa74ed082c6a20f8835b90b'
    contact_id_7 = 7
    
    with Session(engine) as session:
        # 1. Get contact 7 details
        c7 = session.get(Contact, contact_id_7)
        contact_user_id_7 = c7.contact_user_id
        print(f"Contact 7 User ID: {contact_user_id_7}")

        # 2. Simulate the query
        statement = (
            select(Schedule)
            .outerjoin(attend, Schedule.schedule_id == attend.schedule_id)
            .where(Schedule.user_id == user_id)
            .where(
                or_(
                    Schedule.contact_id == contact_id_7,
                    attend.contact_id == contact_id_7,
                    (attend.user_id == contact_user_id_7) if contact_user_id_7 else (attend.contact_id == contact_id_7)
                )
            )
            .distinct()
        )
        
        results = session.exec(statement).all()
        print(f"Found {len(results)} schedules for Contact 7:")
        for s in results:
            print(f"- {s.title} (ID: {s.schedule_id}, Contact: {s.contact_id})")

if __name__ == "__main__":
    debug_query()
