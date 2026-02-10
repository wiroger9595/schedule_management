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

async def create_schedule_attendee_table():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print("Creating 'schedule_attendee' table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS attendee (
                id SERIAL PRIMARY KEY,
                schedule_id INT NOT NULL,
                user_id UUID NOT NULL,
                status VARCHAR(20) DEFAULT 'PENDING',
                PRIMARY KEY (schedule_id, user_id),
                FOREIGN KEY (schedule_id) REFERENCES "schedule" (id),
                FOREIGN KEY (user_id) REFERENCES "user" (id)
            );
        """)
        print("Migration complete!")
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_schedule_attendee_table())
