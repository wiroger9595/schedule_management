import os
from dotenv import load_dotenv
from sqlmodel import create_engine, SQLModel, text
from sqlalchemy import event

# Import models so metadata is populated
from app.models.user import User
from app.models.schedule import Schedule
from app.models.contact import Contact
from app.models.attend import attend

load_dotenv()

postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "schedule_management")
postgres_schema = os.getenv("POSTGRES_SCHEMA")
if not postgres_schema:
    postgres_schema = "public"

SYNC_DATABASE_URL = f"postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

def fix_users_table():
    engine = create_engine(SYNC_DATABASE_URL)

@event.listens_for(engine, "connect")
def set_search_path(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET search_path TO {postgres_schema}")
    cursor.close()

    
    with engine.begin() as conn:
        print("Checking for missing columns in users table...")
        columns_to_add = [
            ("hashed_password", "VARCHAR(255)"),
            ("google_id", "VARCHAR(255)"),
            ("apple_id", "VARCHAR(255)")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type};"))
                print(f"Added {col_name} to users table if it didn't exist.")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")

if __name__ == "__main__":
    fix_users_table()
