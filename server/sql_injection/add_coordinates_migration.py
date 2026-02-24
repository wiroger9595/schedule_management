import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

# Build connection string for asyncpg (postgresql://...)
postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "schedule_management")
postgres_schema = os.getenv("POSTGRES_SCHEMA")
if not postgres_schema:
    postgres_schema = "public"

DATABASE_URL = f"postgresql://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

async def add_columns():
    try:
        print(f"Connecting to {DATABASE_URL}...")
        conn = await asyncpg.connect(DATABASE_URL, server_settings={'search_path': postgres_schema})
        print("Connected to database.")
        
        print("Adding 'latitude' column...")
        await conn.execute("ALTER TABLE schedule ADD COLUMN IF NOT EXISTS latitude FLOAT")
        
        print("Adding 'longitude' column...")
        await conn.execute("ALTER TABLE schedule ADD COLUMN IF NOT EXISTS longitude FLOAT")
        
        print("Migration complete!")
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        if 'conn' in locals():
            await conn.close()

if __name__ == "__main__":
    asyncio.run(add_columns())
