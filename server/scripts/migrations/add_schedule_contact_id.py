import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

# Copy of connection string logic
postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "schedule_management")

DATABASE_URL = os.getenv("DATABASE_URL") or f"postgresql+asyncpg://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

async def add_contact_id_column():
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        try:
            # Add contact_id column
            await conn.execute(text("ALTER TABLE schedule ADD COLUMN IF NOT EXISTS contact_id INTEGER"))
            print("Added column contact_id")
            
            # Add foreign key constraint (optional but good for integrity)
            # We need to make sure contact table exists and has id. 
            # Assuming contact.id is the PK.
            # We won't enforce strict FK constraint right now to avoid issues if data is messy, 
            # or we can try. User asked for "link", implying logic level, but FK is better.
            # Let's just add the column first.
            
        except Exception as e:
            print(f"Error adding contact_id: {e}")

if __name__ == "__main__":
    asyncio.run(add_contact_id_column())
