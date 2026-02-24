import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from sqlmodel import create_engine, text
from sqlalchemy import event
# Try importing config, if fails, define settings manually or read env
try:
    from app.core.config import settings
    DATABASE_URL = settings.DATABASE_URL
except ImportError:
    # Minimal fallback if config import fails
    import os
    from dotenv import load_dotenv
    load_dotenv()
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/schedule_management")

print(f"Using Database URL: {DATABASE_URL}")
engine = create_engine(DATABASE_URL)

@event.listens_for(engine, "connect")
def set_search_path(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET search_path TO {postgres_schema}")
    cursor.close()


def add_meeting_end_time_column():
    print("Attempting to add 'meeting_end_time' column to 'schedule' table...")
    with engine.connect() as connection:
        try:
            # Check if column exists first (PostgreSQL specific check, or just try-except)
            # Simple approach: try add, ignore if exists error
            connection.execute(text("ALTER TABLE schedule ADD COLUMN meeting_end_time VARCHAR(255) NULL;"))
            connection.commit()
            print("Successfully added 'meeting_end_time' column.")
        except Exception as e:
            print(f"Error adding column (it might already exist): {e}")

if __name__ == "__main__":
    add_meeting_end_time_column()
