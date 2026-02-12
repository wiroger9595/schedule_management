from sqlmodel import Session, select, create_engine
from app.models.schedule import Schedule
from app.models.attendee import Attendee
from app.models.enums import Status
from app.core.config import settings

# Database connection
DATABASE_URL = "postgresql://postgres:password@localhost:5432/schedule_db" # Adjust if needed, or use settings logic
try:
    from app.core.config import settings
    DATABASE_URL = str(settings.SQLALCHEMY_DATABASE_URI)
except Exception as e:
    print(f"Could not load settings, using default localhost: {e}")

engine = create_engine(DATABASE_URL)

def migrate_status():
    with Session(engine) as session:
        # 1. Update Schedules
        print("Migrating Schedules...")
        schedules = session.exec(select(Schedule)).all()
        for schedule in schedules:
            old_status = schedule.status
            new_status = old_status

            if old_status == 'PENDING':
                new_status = Status.PENDING
            elif old_status in ['ON_THE_WAY', 'LATE', 'COMPLETED', 'ACTIVE']:
                new_status = Status.ACTIVE
            elif old_status == 'CANCELLED':
                new_status = Status.CANCEL
            elif old_status == 'NOT_GOING':
                new_status = Status.NOT_GOING # Unlikely for schedule but possible
            
            # If it's already a single letter, assume it's correct or map it if needed
            if len(old_status) > 1 and new_status != old_status:
                print(f"Updating Schedule {schedule.id}: {old_status} -> {new_status}")
                schedule.status = new_status
                session.add(schedule)

        # 2. Update Attendees
        print("Migrating Attendees...")
        attendees = session.exec(select(Attendee)).all()
        for attendee in attendees:
            old_status = attendee.status
            new_status = old_status

            if old_status == 'PENDING':
                new_status = Status.PENDING
            elif old_status == 'ACCEPTED':
                new_status = Status.ACTIVE
            elif old_status == 'DECLINED':
                new_status = Status.NOT_GOING
            elif old_status == 'CANCELLED':
                new_status = Status.CANCEL # ??
            
            if len(old_status) > 1 and new_status != old_status:
                print(f"Updating Attendee {attendee.id}: {old_status} -> {new_status}")
                attendee.status = new_status
                session.add(attendee)
        
        session.commit()
        print("Migration complete!")

if __name__ == "__main__":
    migrate_status()
