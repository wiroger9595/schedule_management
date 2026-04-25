"""
Admin API — protected by X-Admin-Key header.
Set ADMIN_SECRET_KEY in .env to enable.
"""
import os
import json
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

load_dotenv()
from sqlmodel import Session, select, func
from sqlalchemy import cast, DateTime as SADateTime
from typing import Optional

from ...db.database import get_session
from ...models.user import User
from ...models.schedule import Schedule
from ...models.attend import attend
from ...models.contact import Contact
from ...models.ai_feedback import AIFeedback

router = APIRouter()


def _check_admin(x_admin_key: Optional[str] = Header(default=None)):
    secret = os.getenv("ADMIN_SECRET_KEY", "")
    if not secret or x_admin_key != secret:
        raise HTTPException(status_code=403, detail="Forbidden")


# ── Overview stats ────────────────────────────────────────────────────────────

@router.get("/stats")
def get_stats(
    session: Session = Depends(get_session),
    _: None = Depends(_check_admin),
):
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_users = session.exec(select(func.count(User.id))).one()
    new_users_week = session.exec(
        select(func.count(User.id)).where(User.created_at >= week_ago)
    ).one()
    new_users_month = session.exec(
        select(func.count(User.id)).where(User.created_at >= month_ago)
    ).one()

    total_schedules = session.exec(select(func.count(Schedule.id))).one()
    schedules_week = session.exec(
        select(func.count(Schedule.id)).where(Schedule.created_at >= week_ago)
    ).one()

    total_contacts = session.exec(select(func.count(Contact.id))).one()
    total_attends = session.exec(select(func.count(attend.attend_id))).one()

    # Schedule status breakdown
    status_rows = session.exec(
        select(Schedule.status, func.count(Schedule.id))
        .group_by(Schedule.status)
    ).all()
    status_breakdown = {row[0]: row[1] for row in status_rows}

    # New users per day (last 14 days)
    daily_users = []
    for i in range(13, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = session.exec(
            select(func.count(User.id)).where(
                User.created_at >= day_start, User.created_at < day_end
            )
        ).one()
        daily_users.append({"date": day_start.strftime("%m/%d"), "count": count})

    # New schedules per day (last 14 days)
    daily_schedules = []
    for i in range(13, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = session.exec(
            select(func.count(Schedule.id)).where(
                Schedule.created_at >= day_start, Schedule.created_at < day_end
            )
        ).one()
        daily_schedules.append({"date": day_start.strftime("%m/%d"), "count": count})

    return {
        "users": {
            "total": total_users,
            "new_this_week": new_users_week,
            "new_this_month": new_users_month,
        },
        "schedules": {
            "total": total_schedules,
            "new_this_week": schedules_week,
            "status_breakdown": status_breakdown,
        },
        "contacts": {"total": total_contacts},
        "attends": {"total": total_attends},
        "charts": {
            "daily_users": daily_users,
            "daily_schedules": daily_schedules,
        },
    }


# ── Users list ────────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(
    page: int = 1,
    page_size: int = 20,
    q: Optional[str] = None,
    name: Optional[str] = None,
    email: Optional[str] = None,
    status: Optional[str] = None,
    created_from: Optional[str] = None,
    created_to: Optional[str] = None,
    session: Session = Depends(get_session),
    _: None = Depends(_check_admin),
):
    offset = (page - 1) * page_size
    stmt = select(User)
    if q:
        stmt = stmt.where(
            User.full_name.ilike(f"%{q}%") | User.email.ilike(f"%{q}%")
        )
    if name:
        stmt = stmt.where(User.full_name.ilike(f"%{name}%"))
    if email:
        stmt = stmt.where(User.email.ilike(f"%{email}%"))
    if status:
        stmt = stmt.where(User.status == status)

    TW_TZ = timezone(timedelta(hours=8))
    
    if created_from:
        try:
            dt_cfrom = datetime.fromisoformat(created_from).replace(tzinfo=TW_TZ)
            stmt = stmt.where(User.created_at >= dt_cfrom)
        except ValueError:
            pass
    if created_to:
        try:
            dt_cto = datetime.fromisoformat(created_to).replace(hour=23, minute=59, second=59, tzinfo=TW_TZ)
            stmt = stmt.where(User.created_at <= dt_cto)
        except ValueError:
            pass

    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    users = session.exec(stmt.order_by(User.created_at.desc()).offset(offset).limit(page_size)).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "user_id": u.user_id,
                "full_name": u.full_name,
                "email": u.email,
                "status": u.status,
                "language": u.language,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


# ── Schedules list ────────────────────────────────────────────────────────────

@router.get("/schedules")
def list_schedules(
    page: int = 1,
    page_size: int = 20,
    q: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    created_from: Optional[str] = None,
    created_to: Optional[str] = None,
    session: Session = Depends(get_session),
    _: None = Depends(_check_admin),
):
    offset = (page - 1) * page_size
    stmt = select(Schedule)
    if q:
        stmt = stmt.where(Schedule.title.ilike(f"%{q}%"))
    if status:
        stmt = stmt.where(Schedule.status == status)
    TW_TZ = timezone(timedelta(hours=8))

    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from).replace(tzinfo=TW_TZ)
            stmt = stmt.where(
                cast(Schedule.meeting_start_time, SADateTime(timezone=True)) >= dt_from
            )
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59, tzinfo=TW_TZ)
            stmt = stmt.where(
                cast(Schedule.meeting_start_time, SADateTime(timezone=True)) <= dt_to
            )
        except ValueError:
            pass
    if created_from:
        try:
            dt_cfrom = datetime.fromisoformat(created_from).replace(tzinfo=TW_TZ)
            stmt = stmt.where(Schedule.created_at >= dt_cfrom)
        except ValueError:
            pass
    if created_to:
        try:
            dt_cto = datetime.fromisoformat(created_to).replace(hour=23, minute=59, second=59, tzinfo=TW_TZ)
            stmt = stmt.where(Schedule.created_at <= dt_cto)
        except ValueError:
            pass

    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    schedules = session.exec(stmt.order_by(Schedule.created_at.desc()).offset(offset).limit(page_size)).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "schedule_id": s.schedule_id,
                "title": s.title,
                "user_id": s.user_id,
                "status": s.status,
                "meeting_location": s.meeting_location,
                "meeting_start_time": s.meeting_start_time.isoformat() if isinstance(s.meeting_start_time, datetime) else str(s.meeting_start_time) if s.meeting_start_time else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in schedules
        ],
    }


# ── AI Training data export ───────────────────────────────────────────────────

@router.get("/training-data")
def export_training_data(
    only_bad: bool = False,
    session: Session = Depends(get_session),
    _: None = Depends(_check_admin),
):
    """Export feedback as JSONL — one line per record, Alpaca/ChatML compatible."""
    stmt = select(AIFeedback)
    if only_bad:
        stmt = stmt.where(AIFeedback.is_good == False)  # noqa: E712
    stmt = stmt.order_by(AIFeedback.created_at.asc())
    rows = session.exec(stmt).all()

    def _generate():
        for r in rows:
            if r.correction:
                # DPO-style: chosen = correction, rejected = ai_reply
                record = {
                    "prompt": r.user_message,
                    "chosen": r.correction,
                    "rejected": r.ai_reply,
                    "is_good": r.is_good,
                    "model_label": r.model_label,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
            else:
                # SFT-style: use ai_reply as the target response
                record = {
                    "instruction": r.user_message,
                    "output": r.ai_reply,
                    "is_good": r.is_good,
                    "model_label": r.model_label,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
            yield json.dumps(record, ensure_ascii=False) + "\n"

    return StreamingResponse(
        _generate(),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": "attachment; filename=training_data.jsonl"},
    )
