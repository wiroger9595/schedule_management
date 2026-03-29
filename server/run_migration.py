from app.db.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("Executing ALTER TABLE...")
    try:
        conn.execute(text("ALTER TABLE schedule_management.schedule ADD COLUMN IF NOT EXISTS is_online BOOLEAN DEFAULT FALSE;"))
        conn.commit()
        print("Migration complete!")
    except Exception as e:
        print(f"Migration error or already exists: {e}")
