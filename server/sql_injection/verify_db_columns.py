from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv
import os

load_dotenv('server/.env')

# Construct DB URL manually to be sure
# Default values from .env or hardcoded fallbacks
user = os.getenv("POSTGRES_USER", "postgres")
password = os.getenv("POSTGRES_PASSWORD", "password")
server = os.getenv("POSTGRES_SERVER", "localhost")
port = os.getenv("POSTGRES_PORT", "5432")
db = os.getenv("POSTGRES_DB", "schedule_management")

url = f"postgresql+psycopg2://{user}:{password}@{server}:{port}/{db}"
print(f"Connecting to: {url}")

try:
    engine = create_engine(url)
    inspector = inspect(engine)
    columns = inspector.get_columns('schedule')
    print("Columns in 'schedule' table:")
    for col in columns:
        print(f"- {col['name']} ({col['type']})")

    has_lat = any(c['name'] == 'latitude' for c in columns)
    has_lon = any(c['name'] == 'longitude' for c in columns)
    
    if has_lat and has_lon:
        print("\nSUCCESS: Latitude and Longitude columns EXIST.")
    else:
        print("\nFAILURE: Latitude and/or Longitude columns are MISSING.")

except Exception as e:
    print(f"\nError: {e}")
