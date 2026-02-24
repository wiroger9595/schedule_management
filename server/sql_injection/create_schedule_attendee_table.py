import asyncio
import os
from dotenv import load_dotenv
import asyncpg

from app.models.enums import Status

load_dotenv()

postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "schedule_management")
postgres_schema = os.getenv("POSTGRES_SCHEMA")
if not postgres_schema:
    postgres_schema = "public"

DATABASE_URL = f"postgresql://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

async def create_schedule_attend_table():
    conn = await asyncpg.connect(DATABASE_URL, server_settings={'search_path': postgres_schema})
    try:
        print("Creating 'schedule_attend' table...")
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS attend (
                id SERIAL PRIMARY KEY,
                schedule_id INT NOT NULL,
                user_id UUID NOT NULL,
                status VARCHAR(20) DEFAULT '{Status.PENDING.value}',
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
    asyncio.run(create_schedule_attend_table())
