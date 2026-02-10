"""
Database migration script to add phone, line_id, and language columns to user table
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def add_user_fields():
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
        # Check and add phone column
        check_phone = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='user' AND column_name='phone';
        """
        result = await conn.fetch(check_phone)
        
        if result:
            print("✓ Column 'phone' already exists")
        else:
            await conn.execute('ALTER TABLE "user" ADD COLUMN phone VARCHAR(20);')
            print("✓ Successfully added 'phone' column to 'user' table")
        
        # Check and add line_id column
        check_line = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='user' AND column_name='line_id';
        """
        result = await conn.fetch(check_line)
        
        if result:
            print("✓ Column 'line_id' already exists")
        else:
            await conn.execute('ALTER TABLE "user" ADD COLUMN line_id VARCHAR(100);')
            print("✓ Successfully added 'line_id' column to 'user' table")
        
        # Check and add language column
        check_lang = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='user' AND column_name='language';
        """
        result = await conn.fetch(check_lang)
        
        if result:
            print("✓ Column 'language' already exists")
        else:
            await conn.execute("ALTER TABLE \"user\" ADD COLUMN language VARCHAR(10) DEFAULT 'zh-TW';")
            print("✓ Successfully added 'language' column to 'user' table")
    
    finally:
        await conn.close()
        print("✓ Database connection closed")

if __name__ == "__main__":
    asyncio.run(add_user_fields())
