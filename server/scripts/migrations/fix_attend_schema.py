from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "schedule_management")

DATABASE_URL = os.getenv("DATABASE_URL") or f"postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

def fix_schema():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        with conn.begin():
            print("Adding missing columns to attend table...")
            try:
                conn.execute(text("ALTER TABLE attend ADD COLUMN IF NOT EXISTS name VARCHAR(255)"))
                print("Added name")
                conn.execute(text("ALTER TABLE attend ADD COLUMN IF NOT EXISTS email VARCHAR(255)"))
                print("Added email")
                conn.execute(text("ALTER TABLE attend ADD COLUMN IF NOT EXISTS phone VARCHAR(50)"))
                print("Added phone")
                conn.execute(text("ALTER TABLE attend ADD COLUMN IF NOT EXISTS line_id VARCHAR(50)"))
                print("Added line_id")
            except Exception as e:
                print(f"Error adding columns: {e}")

if __name__ == "__main__":
    fix_schema()
