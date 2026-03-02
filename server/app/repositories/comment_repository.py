from sqlmodel import Session, select
from typing import List, Optional
import uuid
from datetime import datetime, timezone

from ..models.comment import Comment

class CommentRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_user_id(self, user_id: str) -> List[Comment]:
        # Return all comments for the user, ordered by latest update
        statement = select(Comment).where(Comment.user_id == user_id).order_by(Comment.updated_at.desc())
        return self.session.exec(statement).all()

    def get_by_id(self, id: int) -> Optional[Comment]:
        return self.session.get(Comment, id)

    def create(self, comment_data: Comment) -> Comment:
        # Generate a unique comment_id using ctd prefix and uuid without hyphens
        if not comment_data.comment_id:
            comment_data.comment_id = "ctd" + str(uuid.uuid4()).replace("-", "")
        
        self.session.add(comment_data)
        self.session.commit()
        self.session.refresh(comment_data)
        return comment_data

    def update(self, comment: Comment) -> Comment:
        comment.updated_at = datetime.now(timezone.utc)
        self.session.add(comment)
        self.session.commit()
        self.session.refresh(comment)
        return comment

    def delete(self, comment: Comment) -> None:
        # Soft delete by setting status to 'N'
        comment.status = "N"
        comment.updated_at = datetime.now(timezone.utc)
        self.session.add(comment)
        self.session.commit()
