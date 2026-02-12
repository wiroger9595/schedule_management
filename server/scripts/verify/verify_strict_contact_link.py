from sqlmodel import Session, select, create_engine
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

# Use psycopg2 as per app usage
DATABASE_URL = os.getenv("DATABASE_URL") or f"postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

def verify():
    print(f"Connecting to {DATABASE_URL}...")
    engine = create_engine(DATABASE_URL)

    with Session(engine) as session:
        # 1. Get a user
        try:
            user = session.exec(select(User)).first()
            if not user:
                print("No user found, cannot verify.")
                return
            print(f"Using user: {user.user_id}")
        except Exception as e:
            print(f"Error fetching user: {e}")
            return

        # 2. Test Case A: Create Contact then Schedule with contact_id
        try:
            print("\n--- Test Case A: Existing Contact ---")
            contact = Contact(
                user_id=user.user_id,
                nick_name="Strict Friend A",
                phone="0911223344",
                line_id="strict_line_a"
            )
            session.add(contact)
            session.commit()
            session.refresh(contact)
            print(f"Created Contact A ID: {contact.id}")

            schedule_a = Schedule(
                user_id=user.user_id,
                title="Strict Link Test A",
                contact_id=contact.id
            )
            session.add(schedule_a)
            session.commit()
            session.refresh(schedule_a)
            
            # Verify serialization
            data_a = schedule_a.dict()
            print(f"Schedule A contact_name: {data_a.get('contact_name')}")
            
            if data_a.get('contact_name') == "Strict Friend A":
                print("SUCCESS: Linked via contact_id!")
            else:
                print(f"FAILURE: Expected 'Strict Friend A', got {data_a.get('contact_name')}")
                
        except Exception as e:
            print(f"Error in Test Case A: {e}")
            session.rollback()

        # 3. Test Case B: Manual Details -> Auto-create Contact
        # This logic is in the API endpoint, NOT the model.
        # So we cannot test it here by just creating Schedule model instance.
        # We need to simulate the API logic.
        
        try:
            print("\n--- Test Case B: Auto-create Contact (Simulating API Logic) ---")
            data = {
                "title": "Strict Link Test B",
                "contact_name": "Strict Friend B",
                "contact_phone": "0988776655"
            }
            
            # API Logic Simulation
            start_time_str = "2026-02-12T10:00:00"
            contact_id = data.get("contact_id")
            
            schedule_b = Schedule(
                user_id=user.user_id,
                title=data["title"],
                meeting_time=start_time_str,
                contact_id=contact_id
            )
            
            if not contact_id and (data.get("contact_name") or data.get("contact_phone")):
                print("DEBUG: Auto-creating contact for schedule...")
                new_contact = Contact(
                    user_id=user.user_id,
                    nick_name=data.get("contact_name"),
                    phone=data.get("contact_phone")
                )
                session.add(new_contact)
                session.commit()
                session.refresh(new_contact)
                print(f"DEBUG: Auto-created Contact ID: {new_contact.id}")
                schedule_b.contact_id = new_contact.id
            
            session.add(schedule_b)
            session.commit()
            session.refresh(schedule_b)
            
            # Verify serialization
            data_b = schedule_b.dict()
            print(f"Schedule B contact_name: {data_b.get('contact_name')}")
            print(f"Schedule B contact_id: {data_b.get('contact_id')}")
            
            if data_b.get('contact_name') == "Strict Friend B" and data_b.get('contact_id') is not None:
                print("SUCCESS: Auto-created Contact and linked!")
            else:
                print(f"FAILURE: Expected 'Strict Friend B', got {data_b.get('contact_name')}")
                
        except Exception as e:
            print(f"Error in Test Case B: {e}")
            session.rollback()

        # Cleanup
        try:
            print("\nCleaning up...")
            # Delete schedules first due to FK?
            # session.delete(schedule_a) # might trigger undefined if failed
            # session.delete(schedule_b)
            # session.delete(contact)
            # session.delete(new_contact)
            # Actually just let DB handling or manual cleanup script if needed.
            # But let's try to be clean.
            session.exec(text("DELETE FROM schedule WHERE title LIKE 'Strict Link Test%'"))
            session.exec(text("DELETE FROM contact WHERE nick_name LIKE 'Strict Friend%'"))
            session.commit()
            print("Cleanup done.")
        except Exception as e:
             print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    verify()
