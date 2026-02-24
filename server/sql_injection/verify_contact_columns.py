from sqlalchemy import create_engine, inspect
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

    inspector = inspect(engine)
    columns = inspector.get_columns('contact')
    print("Columns in 'contact' table:")
    for column in columns:
        print(f"- {column['name']} ({column['type']})")
except Exception as e:
    print(f"Error: {e}")
