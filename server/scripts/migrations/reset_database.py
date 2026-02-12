import asyncio
import os
from dotenv import load_dotenv
import asyncpg
from sqlmodel import create_engine, SQLModel, text

# Import definition to ensure metadata is populated
from app.models.user import User
from app.models.schedule import Schedule
from app.models.contact import Contact
from app.models.attend import attend
# (Old models intentionally omitted so they are not created, but we need to drop them)

load_dotenv()

postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "schedule_management")

DATABASE_URL = f"postgresql://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}" # Asyncpg
SYNC_DATABASE_URL = f"postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

async def reset_database():
    print(f"Connecting to {postgres_server}...")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        # 1. Drop all existing tables (CASCADE)
        tables = ["attend", "contact", "schedule_attend", "schedule", "users", "user"] # "user" is old table name
        
        print("Dropping old tables...")
        for table in tables:
            try:
                await conn.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
                print(f"Dropped {table}")
            except Exception as e:
                print(f"Error dropping {table}: {e}")
                
        await conn.close()
        
        # 2. Re-create using SQLModel to get Identity columns correct
        print("Re-creating tables from SQLModel...")
        engine = create_engine(SYNC_DATABASE_URL)
        SQLModel.metadata.create_all(engine)
        
        print("Database reset complete!")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(reset_database())
