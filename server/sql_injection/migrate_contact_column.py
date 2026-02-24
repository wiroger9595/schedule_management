from sqlalchemy import create_engine, text
import os
from sqlalchemy import event
from dotenv import load_dotenv

load_dotenv(dotenv_path="server/.env")

# Construct DATABASE_URL
user = os.getenv("POSTGRES_USER", "postgres")
password = os.getenv("POSTGRES_PASSWORD", "password")
server = os.getenv("POSTGRES_SERVER", "localhost")
port = os.getenv("POSTGRES_PORT", "5432")
db = os.getenv("POSTGRES_DB", "schedule_management")
DATABASE_URL = f"postgresql+psycopg2://{user}:{password}@{server}:{port}/{db}"

print(f"Connecting to: {DATABASE_URL}")

try:
    engine = create_engine(DATABASE_URL)

@event.listens_for(engine, "connect")
def set_search_path(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET search_path TO {postgres_schema}")
    cursor.close()

    with engine.connect() as connection:
        # Check if column exists first to avoid error
        check_sql = text("SELECT column_name FROM information_schema.columns WHERE table_name='contact' AND column_name='owner_id';")
        result = connection.execute(check_sql).fetchone()
        
        if result:
            print("Found 'owner_id' column. Renaming to 'user_id'...")
            rename_sql = text('ALTER TABLE contact RENAME COLUMN owner_id TO user_id;')
            connection.execute(rename_sql)
            connection.commit()
            print("Successfully renamed 'owner_id' to 'user_id'.")
        else:
            print("Column 'owner_id' not found. Checking if 'user_id' exists...")
            check_user_sql = text("SELECT column_name FROM information_schema.columns WHERE table_name='contact' AND column_name='user_id';")
            result_user = connection.execute(check_user_sql).fetchone()
            if result_user:
                print("Column 'user_id' already exists. No action needed.")
            else:
                print("Neither 'owner_id' nor 'user_id' columns found. Please check table schema.")

except Exception as e:
    print(f"Error: {e}")
