import os
from dotenv import load_dotenv
from sqlmodel import create_engine, Session, text

load_dotenv()

postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "schedule_management")
postgres_schema = os.getenv("POSTGRES_SCHEMA", "public")

DATABASE_URL = f"postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

print(f"Loaded POSTGRES_SCHEMA from env: {postgres_schema}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"options": f"-csearch_path={postgres_schema}"}
)

with engine.connect() as conn:
    print("search_path currently is:", conn.execute(text("SHOW search_path")).fetchone()[0])
    
    # Check tables in schedule_management
    schemas = conn.execute(text("SELECT schema_name FROM information_schema.schemata;")).fetchall()
    print("All schemas:", [s[0] for s in schemas])
    
    tables_sm = conn.execute(text(f"SELECT table_name FROM information_schema.tables WHERE table_schema='{postgres_schema}';")).fetchall()
    print(f"Tables in {postgres_schema}:", [t[0] for t in tables_sm])
    
    tables_public = conn.execute(text(f"SELECT table_name FROM information_schema.tables WHERE table_schema='public';")).fetchall()
    print(f"Tables in public:", [t[0] for t in tables_public])
    
    # Check columns in public.users
    cols_pub = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='users';")).fetchall()
    print("Columns in public.users:", [c[0] for c in cols_pub])
    
    # Check columns in schedule_management.users
    cols_sm = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_schema='{postgres_schema}' AND table_name='users';")).fetchall()
    print(f"Columns in {postgres_schema}.users:", [c[0] for c in cols_sm])

