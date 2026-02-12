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

async def create_contact_table():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print("Creating 'contact' table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS contact (
                id INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                contract_id UUID NOT NULL,
                user_id UUID NOT NULL,
                contact_user_id UUID NOT NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                FOREIGN KEY (contact_user_id) REFERENCES "user" (id)
            );
        """)
        
        # Add index for faster lookups
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_contact_user_id ON contact (user_id);")
        
        print("Migration complete!")
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_contact_table())
