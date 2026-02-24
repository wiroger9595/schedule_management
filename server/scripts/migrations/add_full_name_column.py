from sqlmodel import create_engine, Session, text
from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), '../../../.env'))

# Construct database URL
user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
server = os.getenv("POSTGRES_SERVER")
port = os.getenv("POSTGRES_PORT", 5432)
db = os.getenv("POSTGRES_DB")

# Build synchronously compatible connection string
DATABASE_URL = f"postgresql://{user}:{password}@{server}:{port}/{db}?sslmode=require"
engine = create_engine(DATABASE_URL)

with Session(engine) as session:
    try:
        # Check if column exists, add if not
        session.exec(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);"))
        session.commit()
        print("Successfully added full_name column to users table.")
    except Exception as e:
        print(f"Error adding column: {e}")
        session.rollback()
