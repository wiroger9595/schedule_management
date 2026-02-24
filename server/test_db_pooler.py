import os
from dotenv import load_dotenv
from sqlmodel import create_engine, text
from sqlalchemy import event

load_dotenv()

postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "6543")
postgres_db = os.getenv("POSTGRES_DB", "postgres")
postgres_schema = os.getenv("POSTGRES_SCHEMA", "schedule_management")

DATABASE_URL = f"postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

engine = create_engine(DATABASE_URL)

@event.listens_for(engine, "connect")
def set_search_path(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET search_path TO {postgres_schema}")
    cursor.close()

with engine.connect() as conn:
    print("search_path currently is:", conn.execute(text("SHOW search_path")).fetchone()[0])
