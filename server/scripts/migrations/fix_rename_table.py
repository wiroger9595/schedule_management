from sqlalchemy import text, inspect
import sys
import os

# Add the parent directory to sys.path to allow importing app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import engine

def fix_table_rename():
    with engine.connect() as conn:
        try:
            inspector = inspect(conn)
            tables = inspector.get_table_names()
            print(f"Current tables: {tables}")
            
            if 'attendee' in tables and 'attend' not in tables:
                print("Renaming 'attendee' to 'attend'...")
                conn.execute(text("ALTER TABLE attendee RENAME TO attend;"))
                conn.commit()
                print("Table renamed.")
            elif 'attendee' in tables and 'attend' in tables:
                print("Both 'attendee' and 'attend' exist. Accessing 'attend'...")
                # potentially drop attendee if empty? or just ignore
            elif 'attend' in tables:
                print("'attend' table already exists.")
            else:
                 print("'attend' table does not exist and neither does 'attendee'. Migration might be needed to create it.")
                 # In SQLModel, if we run the app, it might create it if not exists.
            
            # Now ensure user_id is nullable in 'attend'
            if 'attend' in tables or ('attendee' in tables and 'attend' not in tables): 
                # after rename, it is 'attend'
                print("Ensuring user_id is nullable in 'attend'...")
                try:
                    conn.execute(text("ALTER TABLE attend ALTER COLUMN user_id DROP NOT NULL;"))
                    conn.commit()
                    print("user_id column is now nullable.")
                except Exception as e:
                    print(f"Error altering column (might already be nullable): {e}")

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    fix_table_rename()
