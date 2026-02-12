import asyncio
import os
from sqlmodel import Session, select, create_engine
from app.models.schedule import Schedule
from app.services.osmnx_service import OSMnxService
from dotenv import load_dotenv

# Setup sync engine for script
load_dotenv()
postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "schedule_management")

DATABASE_URL = f"postgresql://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"
engine = create_engine(DATABASE_URL)

def backfill():
    with Session(engine) as session:
        # Find all schedules with location
        statement = select(Schedule).where(
            Schedule.meeting_location != None,
            Schedule.meeting_location != ""
        )
        schedules = session.exec(statement).all()
        
        print(f"Found {len(schedules)} schedules to re-process...")
        
        for schedule in schedules:
            location = schedule.meeting_location
            # Clean up location string if it already has ", Taipei" appended from previous attempts
            # Actually OSMnxService handles it.
            
            # Since previously stored location might just be "美麗華", we want OSMnxService to handle it with "Taipei" priority
            # But the DB value for location is `美麗華, Taipei` in the log above?
            # No, the log printed `loc_str`.
            # Wait, the log output was `美麗華, Taipei`. 
            # If the DB already has "Taipei", then OSMnx should have found it?
            # Let's just re-run get_coordinates on whatever is in DB.
            
            print(f"Processing '{schedule.title}' at '{location}'...")
            
            coords = OSMnxService.get_coordinates(location)
            if coords:
                lat, lon = coords
                schedule.latitude = lat
                schedule.longitude = lon
                session.add(schedule)
                print(f"  -> Updated: ({lat}, {lon})")
            else:
                print(f"  -> Failed to geocode")
                
        session.commit()
        print("Backfill complete!")

if __name__ == "__main__":
    backfill()
