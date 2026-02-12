from sqlmodel import Session, text
from app.db.database import engine

def add_language_column():
    with Session(engine) as session:
        try:
            # Check if column exists
            session.exec(text("SELECT language FROM users LIMIT 1"))
            print("Column 'language' already exists.")
        except Exception:
            session.rollback()
            print("Column 'language' does not exist. Adding it...")
            try:
                session.exec(text("ALTER TABLE users ADD COLUMN language VARCHAR(10) DEFAULT 'zh-TW'"))
                session.commit()
                print("Column 'language' added successfully.")
            except Exception as e:
                print(f"Failed to add column: {e}")

if __name__ == "__main__":
    add_language_column()
