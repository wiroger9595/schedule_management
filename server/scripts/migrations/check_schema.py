from sqlmodel import create_engine, Session, text
import os
from dotenv import load_dotenv

load_dotenv()

user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
server = os.getenv("POSTGRES_SERVER")
port = os.getenv("POSTGRES_PORT", 6543)
db = os.getenv("POSTGRES_DB")

schema = os.getenv("POSTGRES_SCHEMA", "schedule_management")
print(f"Schema from env: {schema}")

DATABASE_URL = f"postgresql://{user}:{password}@{server}:{port}/{db}?sslmode=require"
engine = create_engine(DATABASE_URL)

try:
    with Session(engine) as session:
        # Check schemas
        result = session.exec(text("SELECT schema_name FROM information_schema.schemata;")).fetchall()
        print([r[0] for r in result])
        
        # Check tables in that schema
        result = session.exec(text(f"SELECT table_name FROM information_schema.tables WHERE table_schema='{schema}'")).fetchall()
        print(f"Tables in {schema}: {[r[0] for r in result]}")

        # Check columns of the users table
        result = session.exec(text(f"SELECT column_name FROM information_schema.columns WHERE table_schema='{schema}' AND table_name='users'")).fetchall()
        print(f"Columns in {schema}.users: {[r[0] for r in result]}")

        # BUT actually, SQLAlchemy runs queries against 'public' by default if not specified properly in engine setup or connection. Let's check public too
        result = session.exec(text(f"SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='users'")).fetchall()
        print(f"Columns in public.users: {[r[0] for r in result]}")

except Exception as e:
    print(f"Error: {e}")
