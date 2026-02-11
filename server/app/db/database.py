from sqlmodel import SQLModel, create_engine, Session
import os
from dotenv import load_dotenv

load_dotenv()

postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "schedule_management")

DATABASE_URL = f"postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

engine = create_engine(DATABASE_URL)

def get_session():
    with Session(engine) as session:
        yield session
