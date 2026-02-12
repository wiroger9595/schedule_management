from sqlalchemy import create_engine, inspect
import os
from dotenv import load_dotenv

load_dotenv()

postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "schedule_management")

DATABASE_URL = os.getenv("DATABASE_URL") or f"postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

def inspect_schema():
    try:
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        columns = inspector.get_columns('schedule')
        print(f"Columns in 'schedule' table:")
        for col in columns:
            print(f"  - {col['name']}: {col['type']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_schema()
