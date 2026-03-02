import sys
import os
from dotenv import load_dotenv

# Load .env
load_dotenv(os.path.join(os.path.dirname(__file__), 'server', '.env'))

# Add server to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from app.db.database import get_session
from app.models.user import User
from sqlmodel import select

try:
    session = next(get_session())
    users = session.exec(select(User).limit(5)).all()
    for u in users:
        print(f"User: {u.full_name}, profile_image_path: {u.profile_image_path}")
except Exception as e:
    print(f"Error: {e}")
