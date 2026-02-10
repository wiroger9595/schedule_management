import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "schedule_management")

DATABASE_URL = f"postgresql://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

async def add_columns():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print("Adding 'type' column...")
        await conn.execute("ALTER TABLE schedule ADD COLUMN IF NOT EXISTS type VARCHAR DEFAULT 'personal'")
        
        print("Adding 'attendees' column...")
        await conn.execute("ALTER TABLE schedule ADD COLUMN IF NOT EXISTS attendees VARCHAR")
        
        print("Adding 'is_reminder' column...")
        await conn.execute("ALTER TABLE schedule ADD COLUMN IF NOT EXISTS is_reminder BOOLEAN DEFAULT FALSE")
        
        print("Migration complete!")
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(add_columns())
