
import sys
import os
from sqlmodel import Session, select

# Add server directory to path
sys.path.append(os.path.join(os.getcwd(), 'server'))

from app.db.database import engine
from app.models.contact import Contact

def debug_contacts():
    with Session(engine) as session:
        c1 = session.get(Contact, 3)
        c2 = session.get(Contact, 7)
        
        print(f"Contact 3: {c1}")
        print(f"Contact 7: {c2}")
        
        if c1 and c2:
            print(f"Contact 3 UserID: {c1.contact_user_id}")
            print(f"Contact 7 UserID: {c2.contact_user_id}")

if __name__ == "__main__":
    debug_contacts()
