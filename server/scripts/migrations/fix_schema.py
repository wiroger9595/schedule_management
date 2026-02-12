from sqlalchemy import text
import sys
import os

# Add the parent directory to sys.path to allow importing app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import engine

def fix_schema():
    with engine.connect() as conn:
        try:
             print("Altering attend table to allow nullable user_id...")
             conn.execute(text("ALTER TABLE attend ALTER COLUMN user_id DROP NOT NULL;"))
             conn.commit()
             print("Success.")
        except Exception as e:
             print(f"Error: {e}")

if __name__ == "__main__":
    fix_schema()
