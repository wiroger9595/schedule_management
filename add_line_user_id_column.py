
import sys
import os
from sqlalchemy import text

# Add server directory to path
sys.path.append(os.path.join(os.getcwd(), 'server'))

def migrate():
    try:
        from app.db.database import engine
        print("Successfully imported engine.")
        
        with engine.connect() as conn:
            # Check table existence
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
            tables = [row[0] for row in result.fetchall()]
            
            target_table = 'users' if 'users' in tables else 'user'
            if target_table not in tables:
                print("Neither 'users' nor 'user' table found.")
                return

            # Check column
            check_sql = text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{target_table}' AND column_name='line_user_id'")
            result = conn.execute(check_sql).fetchone()
            
            if not result:
                print(f"Adding 'line_user_id' column to {target_table}...")
                conn.execute(text(f"ALTER TABLE {target_table} ADD COLUMN line_user_id VARCHAR(255)"))
                conn.execute(text(f"ALTER TABLE {target_table} ADD CONSTRAINT uq_{target_table}_line_user_id UNIQUE (line_user_id)"))
                conn.commit()
                print("Migration successful.")
            else:
                print("'line_user_id' column already exists.")

    except ImportError as e:
        print(f"Import Error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    migrate()
