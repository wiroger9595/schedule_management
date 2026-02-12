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

async def add_columns():
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        columns = [
            ("contact_name", "VARCHAR(255)"),
            ("contact_email", "VARCHAR(255)"),
            ("contact_phone", "VARCHAR(255)"),
            ("contact_line_id", "VARCHAR(255)")
        ]
        
        for col_name, col_type in columns:
            try:
                # Check column existence first to avoid errors
                # Postgres < 9.6 doesn't support IF NOT EXISTS for ADD COLUMN, but newer ones do.
                # Use raw SQL block execution
                await conn.execute(text(f"ALTER TABLE schedule ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
                print(f"Added column {col_name}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")

if __name__ == "__main__":
    asyncio.run(add_columns())
