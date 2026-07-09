from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, select
from typing import List, Optional
from ...db.database import get_session
from ...models.user import User
from ...models.attend import attend
from ...models.schedule import Schedule
from ...repositories.user_repository import UserRepository
from ...repositories.user_device_repository import UserDeviceRepository
from ...schemas.user import UserUpdate, ProfilePictureUpdate, UserRead
from .auth import get_current_user
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

router = APIRouter()


class FCMTokenUpdate(BaseModel):
    fcm_token: str


class DeviceTokenUpdate(BaseModel):
    device_id: str
    platform: str
    fcm_token: str


@router.post("/me/fcm-token")
def update_fcm_token(
    data: FCMTokenUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Legacy endpoint. Registers as a single fallback device per user.
    Kept for backward compatibility with older clients; new clients should
    use POST /me/devices/fcm-token which supports multiple devices per account.
    """
    repo = UserDeviceRepository(session)
    repo.register_or_update(
        user_id=current_user.user_id,
        device_id=f"legacy-{current_user.user_id}",
        platform="unknown",
        fcm_token=data.fcm_token,
    )
    return {"ok": True}


@router.post("/me/devices/fcm-token")
def register_device_token(
    data: DeviceTokenUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Register or update a device's FCM token. Supports multiple devices per account
    (e.g. iPhone + MacBook logged into the same account both receive push reminders)."""
    repo = UserDeviceRepository(session)
    repo.register_or_update(
        user_id=current_user.user_id,
        device_id=data.device_id,
        platform=data.platform,
        fcm_token=data.fcm_token,
    )
    return {"ok": True}


@router.get("/me/devices")
def list_my_devices(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """List all devices registered for the current user."""
    repo = UserDeviceRepository(session)
    devices = repo.get_user_devices(current_user.user_id)
    return [
        {
            "device_id": d.device_id,
            "platform": d.platform,
            "last_registered_at": d.last_registered_at,
        }
        for d in devices
    ]


@router.delete("/me/devices/{device_id}")
def unregister_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Unregister a device (called on logout) so it stops receiving push notifications."""
    repo = UserDeviceRepository(session)
    repo.delete_device(current_user.user_id, device_id)
    return {"ok": True}


@router.get("/me/invitations")
def get_my_invitations(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Return all pending invitations for the current user.
    Matches via attend.user_id OR contact.contact_user_id (handles cases where
    attend.user_id was never set but the contact is linked to this user).
    """
    from ...models.contact import Contact
    from sqlalchemy import or_
    from sqlalchemy.orm import aliased

    LinkedUser = aliased(User)

    stmt = (
        select(attend, Schedule)
        .join(Schedule, attend.schedule_id == Schedule.schedule_id)
        .outerjoin(Contact, attend.contact_id == Contact.id)
        .outerjoin(LinkedUser, Contact.email == LinkedUser.email)
        .where(
            or_(
                attend.user_id == current_user.user_id,
                Contact.contact_user_id == current_user.user_id,
                # Fallback: contact email matches a registered user (look up via users table)
                LinkedUser.user_id == current_user.user_id,
            ),
            attend.status.in_(["P", "AT", "NG"]),
            Schedule.user_id != current_user.user_id,
        )
    )
    rows = session.exec(stmt).all()

    result = []
    seen = set()
    needs_commit = False
    for att, schedule in rows:
        if att.attend_id in seen:
            continue
        seen.add(att.attend_id)

        # Back-fill attend.user_id so future queries are faster
        if att.user_id is None:
            att.user_id = current_user.user_id
            session.add(att)
            needs_commit = True

        # Back-fill contact.contact_user_id if matched by email
        if att.contact_id:
            contact_obj = session.exec(select(Contact).where(Contact.id == att.contact_id)).first()
            if contact_obj and contact_obj.contact_user_id is None and contact_obj.email == current_user.email:
                contact_obj.contact_user_id = current_user.user_id
                session.add(contact_obj)
                needs_commit = True

        inviter = session.exec(select(User).where(User.user_id == schedule.user_id)).first() if schedule.user_id else None
        result.append({
            "attend_id": att.attend_id,
            "schedule_id": schedule.schedule_id,
            "title": schedule.title,
            "start_time": schedule.meeting_start_time if isinstance(schedule.meeting_start_time, str) else (schedule.meeting_start_time.isoformat() if schedule.meeting_start_time else None),
            "location": schedule.meeting_location,
            "inviter_name": inviter.full_name if inviter else "某人",
            "status": att.status,
        })

    if needs_commit:
        session.commit()

    return result


@router.post("/me/invitations/{attend_id}/respond")
def respond_to_invitation(
    attend_id: str,
    action: str,  # "accept" or "decline"
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Accept or decline a pending invitation."""
    if action not in ("accept", "decline"):
        raise HTTPException(status_code=400, detail="action must be 'accept' or 'decline'")

    att = session.exec(select(attend).where(attend.attend_id == attend_id)).first()
    if not att:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if att.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your invitation")

    att.status = "AT" if action == "accept" else "NG"
    att.updated_at = datetime.now()
    session.add(att)

    # Push notification to schedule creator
    schedule = session.exec(
        select(Schedule).where(Schedule.schedule_id == att.schedule_id)
    ).first()

    if schedule:
        creator = session.exec(select(User).where(User.user_id == schedule.user_id)).first() if schedule.user_id else None
        if creator and creator.fcm_token:
            from ...services.push_service import push_service
            verb = "確認參與" if action == "accept" else "拒絕參與"
            push_service.send(
                token=creator.fcm_token,
                title=f"{current_user.full_name or '受邀者'} {verb}了活動",
                body=schedule.title,
                data={"schedule_id": schedule.schedule_id, "type": "rsvp_response"},
            )

    session.commit()
    return {"ok": True, "status": att.status}


@router.get("/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/search", response_model=List[UserRead])
def search_users(q: str, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = UserRepository(session)
    if not q:
        return []
    return repo.search_users(q, exclude_user_id=current_user.user_id)


@router.put("/me/profile_picture", response_model=UserRead)
def update_profile_picture(data: ProfilePictureUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = UserRepository(session)
    image_url = data.image_url
    if not image_url:
        pass

    current_user.profile_image_path = image_url
    return repo.update(current_user)

@router.patch("/me", response_model=UserRead)
def update_user_me(data: UserUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    repo = UserRepository(session)

    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.phone is not None:
        current_user.phone = data.phone
    if data.email is not None:
        current_user.email = data.email
    if data.line_id is not None:
        current_user.line_id = data.line_id
    if data.language is not None:
        current_user.language = data.language

    return repo.update(current_user)

@router.put("/{user_id}", response_model=UserRead)
def update_user_profile(user_id: str, data: UserUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    repo = UserRepository(session)

    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.phone is not None:
        current_user.phone = data.phone
    if data.email is not None:
        current_user.email = data.email
    if data.line_id is not None:
        current_user.line_id = data.line_id
    if data.language is not None:
        current_user.language = data.language

    return repo.update(current_user)

@router.post("/upload-photo")
async def upload_photo(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """上傳用戶頭像到 Cloudinary"""
    from ...services.cloudinary_service import upload_user_photo, delete_user_photo
    
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="只支援 JPG/PNG 格式")
    
    file_data = await file.read()
    
    try:
        repo = UserRepository(session)
        if current_user.public_id:
            # Now we store full public_id, so we can use it directly
            # Fallback for old records if necessary (checking if it looks like a full path)
            old_id = current_user.public_id
            if "/" not in old_id:
                # Legacy support: if we only have filename, assume old path structure
                old_id = f"user-photo/{current_user.user_id}/{old_id}"
            
            delete_user_photo(old_id)

        result = upload_user_photo(
            str(current_user.user_id),
            file_data,
            file.filename
        )
        
        current_user.profile_image_path = result['url']
        current_user.public_id = result['public_id'] # Store full public_id
        current_user.updated_at = datetime.now()
        
        repo.update(current_user)
        
        return {"photo_url": result['url'], "message": "頭像上傳成功"}
    except Exception as e:
        logger.info(f"Error uploading photo: {e}")
        raise HTTPException(status_code=500, detail=f"上傳失敗：{str(e)}")
