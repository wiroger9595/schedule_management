import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "schedule_management")
postgres_schema = os.getenv("POSTGRES_SCHEMA", "public")

DATABASE_URL = f"postgresql://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

async def main():
    conn = await asyncpg.connect(DATABASE_URL, server_settings={'search_path': postgres_schema})
    rows = await conn.fetch(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = '{postgres_schema}' AND table_name = 'users'")
    for row in rows:
        print(row['column_name'], row['data_type'])
    await conn.close()

asyncio.run(main())
