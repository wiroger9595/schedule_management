from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
import uuid
from datetime import datetime, timezone

from ...db.database import get_session
from ...models.comment import Comment
from ...models.user import User
from ...repositories.comment_repository import CommentRepository
from ...schemas.comment import CommentCreate, CommentRead, CommentUpdate
from .auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[CommentRead])
@router.get("", response_model=List[CommentRead], include_in_schema=False)
def get_comments(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = CommentRepository(session)
    return repo.get_by_user_id(current_user.user_id)

@router.post("/", response_model=CommentRead)
@router.post("", response_model=CommentRead, include_in_schema=False)
def create_comment(comment_data: CommentCreate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = CommentRepository(session)
    # create the true DB model from Pydantic schema
    comment = Comment(
        comment_id="ctd" + str(uuid.uuid4()).replace("-", ""),
        comment_description=comment_data.comment_description,
        user_id=current_user.user_id,
        status=comment_data.status or "P",
    )
    return repo.create(comment)

@router.put("/{contact_id}", response_model=CommentRead)
@router.put("/{contact_id}/", response_model=CommentRead, include_in_schema=False)
def update_comment(
    contact_id: int, 
    comment_data: CommentUpdate, 
    current_user: User = Depends(get_current_user), 
    session: Session = Depends(get_session)
):
    repo = CommentRepository(session)
    # The param is called contact_id for URL path conventionally, but it represents the comment's PK id
    # Let's cleanly alias it to comment_id param below, or just use it as id
    comment = repo.get_by_id(contact_id)
    
    if not comment or comment.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Comment not found")
        
    if comment_data.comment_description is not None:
        comment.comment_description = comment_data.comment_description
    if comment_data.status is not None:
        comment.status = comment_data.status

    return repo.update(comment)

@router.delete("/{contact_id}")
def delete_comment(contact_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = CommentRepository(session)
    comment = repo.get_by_id(contact_id)
    if not comment or comment.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Comment not found")
        
    repo.delete(comment)
    return {"msg": "Deleted"}
