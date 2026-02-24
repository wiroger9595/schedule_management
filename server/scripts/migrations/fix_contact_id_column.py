from sqlalchemy import create_engine, text
import os
from sqlalchemy import event
from dotenv import load_dotenv

load_dotenv()

postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "schedule_management")
postgres_schema = os.getenv("POSTGRES_SCHEMA")
if not postgres_schema:
    postgres_schema = "public"

DATABASE_URL = os.getenv("DATABASE_URL") or f"postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

def fix_column():
    engine = create_engine(DATABASE_URL)

@event.listens_for(engine, "connect")
def set_search_path(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET search_path TO {postgres_schema}")
    cursor.close()

    with engine.connect() as conn:
        print("Dropping existing contact_id column (ARRAY)...")
        # Ensure we are in a transaction block if needed, but for DDL auto-commit is often required or implicit commit.
        # SQLAlchemy Connection.execute auto-commits for DDL in some versions/drivers, but explicit commit is safer.
        with conn.begin():
             conn.execute(text("ALTER TABLE schedule DROP COLUMN contact_id"))
             print("Dropped contact_id")
             conn.execute(text("ALTER TABLE schedule ADD COLUMN contact_id INTEGER"))
             print("Added contact_id as INTEGER")

if __name__ == "__main__":
    fix_column()
