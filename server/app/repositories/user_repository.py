from typing import Optional
from sqlmodel import Session, select
from ..models.user import User

class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_email(self, email: str) -> Optional[User]:
        return self.session.exec(select(User).where(User.email == email)).first()

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.session.exec(select(User).where(User.user_id == user_id)).first()

    def create(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def update(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def search_users(self, query: str, exclude_user_id: Optional[str] = None) -> list[User]:
        from sqlmodel import or_
        like = f"%{query}%"
        statement = select(User).where(
            or_(
                User.phone == query,
                User.line_id == query,
                User.email.ilike(like),
                User.full_name.ilike(like),
            )
        )
        if exclude_user_id:
            statement = statement.where(User.user_id != exclude_user_id)
        return self.session.exec(statement).all()

