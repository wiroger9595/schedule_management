from app.db.database import engine, postgres_schema
from sqlmodel import Session, text

try:
    with Session(engine) as session:
        result = session.exec(text(f"""
            SELECT conname, pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_namespace n ON n.oid = c.connamespace
            WHERE n.nspname = '{postgres_schema}'
            AND conname LIKE 'contact_%';
        """)).fetchall()
        for r in result:
            print(f"Constraint: {r[0]}, Def: {r[1]}")
except Exception as e:
    print(f"ERROR: {e}")
