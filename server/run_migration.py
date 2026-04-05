from app.db.database import engine
from sqlalchemy import text

migrations = [
    "ALTER TABLE schedule_management.schedule ADD COLUMN IF NOT EXISTS is_online BOOLEAN DEFAULT FALSE;",
    "ALTER TABLE schedule_management.users ADD COLUMN IF NOT EXISTS fcm_token VARCHAR(512);",
]

with engine.connect() as conn:
    for sql in migrations:
        print(f"Running: {sql[:60]}...")
        try:
            conn.execute(text(sql))
            conn.commit()
            print("  OK")
        except Exception as e:
            print(f"  Error (may already exist): {e}")
print("Migrations done.")
