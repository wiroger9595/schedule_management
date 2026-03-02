from app.db.database import get_session
from app.models.user import User
from sqlmodel import select

session = next(get_session())
users = session.exec(select(User).limit(5)).all()
for u in users:
    print(f"User: {u.full_name}, profile_image_path: {u.profile_image_path}")
