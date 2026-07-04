
from fastapi import APIRouter, Header, Request, HTTPException, Depends
from sqlmodel import Session, select
from ...db.database import get_session
from ...models.user import User
from ...services.line_service import line_service
from ...core.redis_client import redis_client
from .auth import get_current_user
import random
import string
import json
import logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/webhook")
async def line_webhook(
    request: Request,
    x_line_signature: str = Header(None)
):
    if not x_line_signature:
        raise HTTPException(status_code=400, detail="Missing Signature")
    
    body = await request.body()
    body_str = body.decode('utf-8')
    
    try:
        # Verify signature and parse events
        events = line_service.handler.parser.parse(body_str, x_line_signature)
        
        for event in events:
            # Handle Text Message (for binding)
            if event.type == 'message' and event.message.type == 'text':
                user_message = event.message.text.strip()
                line_user_id = event.source.user_id
                
                # Check if this is a binding code (6 digits)
                if len(user_message) == 6 and user_message.isdigit():
                    # Look up code in Redis
                    # Key: "line_bind:{code}" -> Value: "user_internal_id"
                    # Using global redis_client.client directly to access generic get/delete
                    user_internal_id = redis_client.client.get(f"line_bind:{user_message}")
                    
                    if user_internal_id:
                        # Perform binding in DB
                        from ...db.database import engine
                        with Session(engine) as session:
                            user = session.exec(select(User).where(User.id == int(user_internal_id))).first()
                            if user:
                                user.line_user_id = line_user_id
                                session.add(user)
                                session.commit()
                                
                                line_service.push_message(line_user_id, "綁定成功！您現在可以接收通知了。")
                                redis_client.client.delete(f"line_bind:{user_message}")
                            else:
                                line_service.push_message(line_user_id, "綁定失敗：找不到對應用戶。")
                    else:
                        line_service.push_message(line_user_id, "驗證碼無效或是已過期。")
                else:
                    # Echo or ignore
                    pass
                    
    except Exception as e:
        logger.info(f"Webhook Error: {e}")
        # Build URL for Line Webhook verification
        # Line sends a verification event which might fail signature if not configured correctly or using mock
        # For now return 200 to keep Line happy logic
        return {"status": "OK"}

    return {"status": "OK"}

@router.post("/bind")
async def generate_bind_code(
    current_user: User = Depends(get_current_user)
):
    """Generate a 6-digit code for Line binding"""
    code = ''.join(random.choices(string.digits, k=6))
    
    # Store in Redis: code -> user_id, expire in 5 mins
    redis_client.client.setex(f"line_bind:{code}", 300, str(current_user.id))
    
    return {"code": code, "expires_in": 300}

@router.post("/unbind")
async def unbind_line(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Unbind Line account"""
    current_user.line_user_id = None
    session.add(current_user)
    session.commit()
    return {"status": "success"}
