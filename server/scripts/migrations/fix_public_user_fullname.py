from sqlmodel import create_engine, Session, text
import os
from dotenv import load_dotenv

load_dotenv()

user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
server = os.getenv("POSTGRES_SERVER")
port = os.getenv("POSTGRES_PORT", 6543)
db = os.getenv("POSTGRES_DB")

# Build synchronously compatible connection string
DATABASE_URL = f"postgresql://{user}:{password}@{server}:{port}/{db}?sslmode=require"
engine = create_engine(DATABASE_URL)

with Session(engine) as session:
    try:
        print(f"Adding full_name column to public.users")
        session.exec(text(f"ALTER TABLE public.users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);"))
        session.commit()
        print(f"Successfully added full_name column to public.users table.")
    except Exception as e:
        print(f"Error adding column: {e}")
        session.rollback()
