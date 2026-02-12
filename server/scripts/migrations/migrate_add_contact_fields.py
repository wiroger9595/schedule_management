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

async def migrate():
    print(f"Connecting to {postgres_server}...")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        columns = [
            "contact_name",
            "contact_email",
            "contact_phone",
            "contact_line_id"
        ]
        
        print("Adding contact columns to schedule table...")
        for col in columns:
            try:
                await conn.execute(f'ALTER TABLE schedule ADD COLUMN IF NOT EXISTS {col} VARCHAR(255);')
                print(f"Successfully added {col} column.")
            except Exception as e:
                print(f"Error adding {col}: {e}")
            
        await conn.close()
        print("Migration complete!")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
