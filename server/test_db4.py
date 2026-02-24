import asyncio
import os
import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
load_dotenv()

postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "schedule_management")
postgres_schema = os.getenv("POSTGRES_SCHEMA", "public")

DATABASE_URL = f"postgresql://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

def main():
    # Also test the SQLAlchemy connection
    from sqlmodel import create_engine, SQLModel
    SYNC_DATABASE_URL = f"postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"
    engine = create_engine(
        SYNC_DATABASE_URL,
        connect_args={"options": f"-c search_path={postgres_schema}"}
    )
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{postgres_schema}";'))
        
    from app.models.user import User
    from app.models.schedule import Schedule
    from app.models.contact import Contact
    from app.models.attend import attend
    
    SQLModel.metadata.create_all(engine)
    
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT table_name FROM information_schema.tables WHERE table_schema='{postgres_schema}';")).fetchall()
        print(f"Tables in {postgres_schema}:", [r[0] for r in result])
        
if __name__ == "__main__":
    main()
