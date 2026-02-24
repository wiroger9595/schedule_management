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
    conn = psycopg2.connect(DATABASE_URL, options=f"-c search_path={postgres_schema}")
    cur = conn.cursor()
    cur.execute("SELECT current_schema();")
    print("search_path is:", cur.fetchone()[0])
    
    # Also test the SQLAlchemy connection
    from sqlmodel import create_engine
    SYNC_DATABASE_URL = f"postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"
    engine = create_engine(
        SYNC_DATABASE_URL,
        connect_args={"options": f"-c search_path={postgres_schema}"}
    )
    with engine.connect() as conn2:
        result = conn2.execute(text("SHOW search_path")).fetchone()
        print("SQLAlchemy search_path is:", result[0])

if __name__ == "__main__":
    main()
