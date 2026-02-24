from sqlmodel import Session, select, create_engine
from sqlalchemy import event
from app.models.user import User
from app.models.contact import Contact
from app.models.schedule import Schedule
from app.models.attend import attend
import os
from dotenv import load_dotenv

# We need to make sure we can import app
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "schedule_management")
postgres_schema = os.getenv("POSTGRES_SCHEMA")
if not postgres_schema:
    postgres_schema = "public"

# Use psycopg2 as per app usage
DATABASE_URL = os.getenv("DATABASE_URL") or f"postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

def verify():
    print(f"Connecting to {DATABASE_URL}...")
    try:
        engine = create_engine(DATABASE_URL)

@event.listens_for(engine, "connect")
def set_search_path(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET search_path TO {postgres_schema}")
    cursor.close()

        # Test connection
        with engine.connect() as connection:
            pass
    except Exception as e:
        print(f"Connection failed: {e}")
        print("Trying to install psycopg2-binary...")
        os.system("pip install psycopg2-binary")
        engine = create_engine(DATABASE_URL)

@event.listens_for(engine, "connect")
def set_search_path(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET search_path TO {postgres_schema}")
    cursor.close()


    with Session(engine) as session:
        # 1. Get a user
        try:
            print("Fetching user...")
            user = session.exec(select(User)).first()
            if not user:
                print("No user found, cannot verify.")
                return
            print(f"Using user: {user.user_id}")
        except Exception as e:
            print(f"Error fetching user: {e}")
            return

        # 2. Create a Contact
        try:
            print("Creating Contact...")
            contact = Contact(
                user_id=user.user_id,
                nick_name="Test Friend Sync",
                phone="0911223344",
                email="sync_test@example.com",
                line_id="sync_line"
            )
            session.add(contact)
            session.commit()
            session.refresh(contact)
            print(f"Created Contact ID: {contact.id}")
        except Exception as e:
            print(f"Error creating Contact: {e}")
            session.rollback()
            return

        # 3. Create a Schedule with contact_id
        try:
            print("Creating Schedule...")
            schedule = Schedule(
                user_id=user.user_id,
                title="Meeting with Test Friend Sync",
                contact_id=contact.id
            )
            session.add(schedule)
            session.commit()
            session.refresh(schedule)
            print(f"Created Schedule ID: {schedule.schedule_id} with contact_id: {schedule.contact_id}")
        except Exception as e:
            print(f"Error creating Schedule: {e}")
            session.rollback()
            # Try to cleanup contact
            session.delete(contact)
            session.commit()
            return

        # 4. Verify fetching populates contact details
        try:
            # Access relationship
            print("Accessing schedule.contact...")
            print(f"Schedule contact: {schedule.contact}")
            print("Accessing schedule.dict()...")
            data = schedule.dict()
            print(f"Serialized Data contact_name: {data.get('contact_name')}")
                 
            if data.get('contact_name') == "Test Friend Sync":
                print("SUCCESS: Contact linked correctly!")
            else:
                print(f"FAILURE: Expected 'Test Friend Sync', got {data.get('contact_name')}")
        except Exception as e:
            print(f"Error verifying contact link: {e}")

        # Cleanup
        try:
            print("Cleaning up...")
            session.delete(schedule)
            session.delete(contact)
            session.commit()
        except Exception as e:
             print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    verify()
