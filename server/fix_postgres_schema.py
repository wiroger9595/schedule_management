import os
import re

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
        
    original = content
        
    # Inject postgres_schema fetching after postgres_db if not exists
    db_env_pattern = r'(postgres_db = os\.getenv\("POSTGRES_DB"[^\n]*\n)'
    if re.search(db_env_pattern, content) and "postgres_schema = os.getenv" not in content:
        replacement = r'\1postgres_schema = os.getenv("POSTGRES_SCHEMA")\nif not postgres_schema:\n    postgres_schema = "public"\n'
        content = re.sub(db_env_pattern, replacement, content)

    # 1. Provide sqlalchemy.event import
    if "from sqlalchemy import event" not in content and "create_engine" in content:
        import_pattern = r'(from sqlmodel import.*create_engine.*)'
        if re.search(import_pattern, content):
            content = re.sub(import_pattern, r'\1\nfrom sqlalchemy import event', content)
        else:
            # Maybe just standard import
            import_sqlalchemy = r'(import os)'
            content = re.sub(import_sqlalchemy, r'\1\nfrom sqlalchemy import event', content)

    # 2. Fix engine = create_engine(...) blocks
    # We want to remove the connect_args options we added earlier
    engine_with_options_pattern = r'engine = create_engine\(\s*(SYNC_DATABASE_URL|DATABASE_URL),\s*connect_args=\{"options": f"-c ?search_path=\{postgres_schema\}"\}\s*\)'
    content = re.sub(engine_with_options_pattern, r'engine = create_engine(\1)', content)

    # Now, find `engine = create_engine(...)` and append the event listener if not exists
    event_listener_code = """
@event.listens_for(engine, "connect")
def set_search_path(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET search_path TO {postgres_schema}")
    cursor.close()
"""
    if "def set_search_path(dbapi_connection" not in content and "engine = create_engine(" in content:
        # Just stick it after the engine line
        engine_line_pattern = r'(engine = create_engine\([^\)]+\))'
        content = re.sub(engine_line_pattern, r'\1\n' + event_listener_code, content)
        
    # Same thing for raw psycopg2 connections not using SQLAlchemy
    psycopg_pattern = r'conn = psycopg2\.connect\(DATABASE_URL, options=f"-c search_path=\{postgres_schema\}"\)'
    psycopg_repl = r'conn = psycopg2.connect(DATABASE_URL)\n    with conn.cursor() as cur:\n        cur.execute(f"SET search_path TO {postgres_schema}")\n'
    if 'psycopg2.connect(DATABASE_URL, options=' in content:
        content = re.sub(psycopg_pattern, psycopg_repl, content)

    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Updated {filepath}")

def process_directory(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                fix_file(filepath)

if __name__ == "__main__":
    process_directory("/Users/chenrobert/Documents/code_life/schedule_management/server/scripts")
    process_directory("/Users/chenrobert/Documents/code_life/schedule_management/server/sql_injection")
    process_directory("/Users/chenrobert/Documents/code_life/schedule_management/server/app")
