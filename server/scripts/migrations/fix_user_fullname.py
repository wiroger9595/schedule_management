from sqlmodel import create_engine, Session, text
import os
from dotenv import load_dotenv

load_dotenv()

# Construct database URL
user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
server = os.getenv("POSTGRES_SERVER")
port = os.getenv("POSTGRES_PORT", 6543)
db = os.getenv("POSTGRES_DB")

schema = os.getenv("POSTGRES_SCHEMA", "schedule_management")

# Build synchronously compatible connection string
DATABASE_URL = f"postgresql://{user}:{password}@{server}:{port}/{db}?sslmode=require"
engine = create_engine(DATABASE_URL)

with Session(engine) as session:
    try:
        # Check if column exists, add if not
        print(f"Adding full_name column to {schema}.users")
        session.exec(text(f"CREATE SCHEMA IF NOT EXISTS {schema};"))
        session.exec(text(f"ALTER TABLE {schema}.users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);"))
        session.commit()
        print(f"Successfully added full_name column to {schema}.users table.")
    except Exception as e:
        print(f"Error adding column: {e}")
        session.rollback()
