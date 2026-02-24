from sqlmodel import create_engine, Session, select
from app.models.user import User
import os
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()
postgres_schema = os.getenv("POSTGRES_SCHEMA", "schedule_management")
user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
server = os.getenv("POSTGRES_SERVER")
port = os.getenv("POSTGRES_PORT", 6543)
db = os.getenv("POSTGRES_DB")

DATABASE_URL = f"postgresql+psycopg2://{user}:{password}@{server}:{port}/{db}"

# We use schema_translate_map
engine = create_engine(
    DATABASE_URL,
    execution_options={"schema_translate_map": {None: postgres_schema}},
    echo=True
)

try:
    with Session(engine) as session:
        # test direct query
        users = session.exec(select(User).limit(1)).fetchall()
        print(f"Users found via metadata translation: {len(users)}")
        
        # also test raw SQL text routing if that matters? text() doesn't auto-translate unless bound
        res = session.exec(text("SELECT * FROM users LIMIT 1")).fetchall()
        print(f"Users found via raw SQL: {len(res)}")
except Exception as e:
    print(f"ERROR: {e}")
