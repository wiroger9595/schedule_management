from sqlalchemy import text, inspect
import sys
import os

# Add the parent directory to sys.path to allow importing app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import engine

def add_contact_id_column():
    with engine.connect() as conn:
        try:
            inspector = inspect(conn)
            columns = [c['name'] for c in inspector.get_columns('attend')]
            print(f"Current 'attend' columns: {columns}")
            
            if 'contact_id' not in columns:
                print("Adding 'contact_id' column to 'attend' table...")
                # Assuming contact.id is Integer
                conn.execute(text("ALTER TABLE attend ADD COLUMN contact_id INTEGER;"))
                conn.commit()
                print("Column added.")
            else:
                print("'contact_id' already exists.")

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    add_contact_id_column()
