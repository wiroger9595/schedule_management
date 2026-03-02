from app.db.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("Executing ALTER TABLE...")
    # Add column if not exists
    try:
        conn.execute(text("ALTER TABLE schedule_management.contact ADD COLUMN default_notification_method VARCHAR(255) DEFAULT 'mobile';"))
        conn.commit()
        print("Migration complete!")
    except Exception as e:
        print(f"Migration error or already exists: {e}")
