import asyncio
from datetime import datetime
from sqlmodel import Session, select
from app.db.database import engine
from app.models.schedule import Schedule

with Session(engine) as session:
    stmt = select(Schedule)
    date_from = "2026-04-12"
    date_to = "2026-04-13"
    try:
        stmt = stmt.where(Schedule.meeting_start_time >= datetime.fromisoformat(date_from))
        dt_to = datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59)
        stmt = stmt.where(Schedule.meeting_start_time <= dt_to)
        
        results = session.exec(stmt).all()
        print(f"Results matched: {len(results)}")
        for r in results:
            print(f"- {r.meeting_start_time} (Title: {r.title})")
            
    except Exception as e:
        print(f"Error: {e}")
