
import sys
import os
from sqlmodel import Session, select

sys.path.append(os.path.join(os.getcwd(), 'server'))

from app.db.database import engine
from app.models.schedule import Schedule
from app.models.attend import attend
from app.models.contact import Contact
from app.models.user import User

def debug_schedule():
    with Session(engine) as session:
        # Find the schedule
        schedules = session.exec(select(Schedule).where(Schedule.title.like("%淡水碼頭%"))).all()
        
        for s in schedules:
            print(f"Schedule: {s.title} (ID: {s.schedule_id})")
            print(f"  - Owner: {s.user_id}")
            print(f"  - Main Contact ID: {s.contact_id}")
            
            # Check attends
            attends = session.exec(select(attend).where(attend.schedule_id == s.schedule_id)).all()
            print(f"  - Attendees: {len(attends)}")
            for a in attends:
                print(f"    - Attendee: contact_id={a.contact_id}, user_id={a.user_id}")

if __name__ == "__main__":
    debug_schedule()
