"""
Database migration script to add profile_picture column to user table
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def add_profile_picture_column():
    # Construct database URL
    db_user = os.getenv("POSTGRES_USER", "user")
    db_password = os.getenv("POSTGRES_PASSWORD", "password")
    db_server = os.getenv("POSTGRES_SERVER", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "schedule_management")
    
    database_url = f"postgresql://{db_user}:{db_password}@{db_server}:{db_port}/{db_name}"
    
    print(f"Connecting to database: {db_name}")
    
    # Connect to database
    conn = await asyncpg.connect(database_url)
    
    try:
        # Check if column already exists
        check_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='user' AND column_name='profile_picture';
        """
        result = await conn.fetch(check_query)
        
        if result:
            print("✓ Column 'profile_picture' already exists")
        else:
            # Add the column
            alter_query = 'ALTER TABLE "user" ADD COLUMN profile_picture VARCHAR;'
            await conn.execute(alter_query)
            print("✓ Successfully added 'profile_picture' column to 'user' table")
    
    finally:
        await conn.close()
        print("✓ Database connection closed")

if __name__ == "__main__":
    asyncio.run(add_profile_picture_column())
