from sqlmodel import Session, select, create_engine
from sqlalchemy import event
from app.models.schedule import Schedule
from app.models.attend import attend
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

@event.listens_for(engine, "connect")
def set_search_path(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET search_path TO {postgres_schema}")
    cursor.close()


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
            elif old_status in ['ON_THE_WAY', 'LATE', 'COMPLETED', 'ACTIVE', 'ATTEND']:
                new_status = Status.ATTEND
            elif old_status == 'ATTEND':
                new_status = Status.CANCEL
            elif old_status == 'CANCEL':
                new_status = Status.CANCEL
            elif old_status == 'NOT_ATTEND':
                new_status = Status.NOT_ATTEND 
            
            # If it's already a single letter, assume it's correct or map it if needed
            if len(old_status) > 1 and new_status != old_status:
                print(f"Updating Schedule {schedule.id}: {old_status} -> {new_status}")
                schedule.status = new_status
                session.add(schedule)

        # 2. Update attends
        print("Migrating attends...")
        attends = session.exec(select(attend)).all()
        for attend in attends:
            old_status = attend.status
            new_status = old_status

            if old_status == 'PENDING':
                new_status = Status.PENDING
            elif old_status == 'ACCEPTED':
                new_status = Status.ACTIVE
            elif old_status == 'DECLINED':
                new_status = Status.NOT_GOING
            elif old_status == 'ATTEND':
                new_status = Status.CANCEL
            elif old_status == 'CANCEL':
                new_status = Status.CANCEL
            elif old_status == 'NOT_ATTEND':
                new_status = Status.NOT_ATTEND 
            
            if len(old_status) > 1 and new_status != old_status:
                print(f"Updating attend {attend.id}: {old_status} -> {new_status}")
                attend.status = new_status
                session.add(attend)
        
        session.commit()
        print("Migration complete!")

if __name__ == "__main__":
    migrate_status()
