from typing import Generic, TypeVar, Type, List, Optional
from datetime import datetime
import logging
from sqlmodel import Session, select, or_
from ..models.schedule import Schedule
from ..models.attend import attend
from ..models.contact import Contact
from ..models.enums import Status
from ..services.reminder_service import ReminderService

logger = logging.getLogger(__name__)

class ScheduleRepository:
    def __init__(self, session: Session):
        self.session = session

    def _refresh_reminder(self, schedule: Schedule) -> None:
        """Recompute the departure-reminder time and (re)schedule all background push jobs.
        Cancelled schedules get their pending jobs removed instead.

        The leave-by computation can hit the OSMnx/Overpass network, so when the
        scheduler is available the whole refresh runs as an immediate background
        job instead of blocking the HTTP request."""
        try:
            from ..services.background_reminder_scheduler import get_reminder_scheduler
            scheduler = get_reminder_scheduler()
            if schedule.status == Status.CANCEL.value:
                if scheduler:
                    scheduler.remove_all_reminders(schedule.schedule_id)
                return
            if scheduler:
                scheduler.refresh_reminders_async(schedule.schedule_id, schedule.user_id)
            else:
                # No scheduler (tests / scripts): compute synchronously so
                # reminder_leave_by_time is still populated.
                ReminderService.compute_and_update_leave_by_time(schedule, self.session)
        except Exception as e:
            logger.warning(f"Failed to refresh reminder for schedule {schedule.schedule_id}: {e}")

    def get_by_id(self, id: int) -> Optional[Schedule]:
        return self.session.get(Schedule, id)

    def get_by_schedule_id(self, schedule_id: str) -> Optional[Schedule]:
        return self.session.exec(select(Schedule).where(Schedule.schedule_id == schedule_id)).first()

    def get_all(self) -> List[Schedule]:
        return self.session.exec(select(Schedule)).all()

    def get_by_user_id(self, user_id: str) -> List[Schedule]:
        # Return schedules created by the user OR where the user is an attendee.
        # Attendee matching covers three cases:
        #   1. attend.user_id == user_id  (directly linked)
        #   2. attend.contact_id -> Contact.contact_user_id == user_id  (linked via contact email match)
        from sqlalchemy import and_
        from sqlalchemy.orm import selectinload
        statement = (
            select(Schedule)
            .outerjoin(attend, Schedule.schedule_id == attend.schedule_id)
            .outerjoin(Contact, attend.contact_id == Contact.id)
            .where(
                or_(
                    Schedule.user_id == user_id,
                    attend.user_id == user_id,
                    and_(Contact.id.isnot(None), Contact.contact_user_id == user_id)
                )
            )
            .distinct()
            # Schedule.dict() serializes attend_records + contact; preload them
            # here or listing N schedules costs 1+2N lazy-load queries.
            .options(
                selectinload(Schedule.attend_records),
                selectinload(Schedule.contact),
            )
        )
        return self.session.exec(statement).all()

    def create(self, schedule: Schedule) -> Schedule:
        self.session.add(schedule)
        self.session.commit()
        self.session.refresh(schedule)
        # Compute and schedule departure reminder
        self._refresh_reminder(schedule)
        return schedule

    def update(self, schedule: Schedule) -> Schedule:
        self.session.add(schedule)
        self.session.commit()
        self.session.refresh(schedule)
        # Recompute and reschedule departure reminder
        self._refresh_reminder(schedule)
        return schedule

    def delete(self, schedule: Schedule) -> None:
        schedule_id = schedule.schedule_id
        self.session.delete(schedule)
        self.session.commit()
        try:
            from ..services.background_reminder_scheduler import get_reminder_scheduler
            scheduler = get_reminder_scheduler()
            if scheduler:
                scheduler.remove_all_reminders(schedule_id)
        except Exception as e:
            logger.warning(f"Failed to remove reminders for deleted schedule {schedule_id}: {e}")

    def get_schedules_with_contact(self, user_id: str, contact_id: int) -> List[Schedule]:
        """
        Fetch schedules where the contact (or linked user) is involved.
        Only returns schedules created by the current user.
        """
        # 1. Get the contact to check for linked user_id
        contact = self.session.get(Contact, contact_id)
        if not contact:
            return []
            
        contact_user_id = contact.contact_user_id
        
        # 2. Build Query
        # Schedules created by current_user
        # AND (
        #   Schedule.contact_id == contact_id 
        #   OR contact is in attend_records VIA contact_id 
        #   OR via user_id
        # )
        
        # 2. Build Query
        conditions = [
            Schedule.contact_id == contact_id,
            attend.contact_id == contact_id
        ]
        
        if contact_user_id:
            conditions.append(attend.user_id == contact_user_id)
            
        statement = (
            select(Schedule)
            .outerjoin(attend, Schedule.schedule_id == attend.schedule_id)
            .where(Schedule.user_id == user_id)
            .where(or_(*conditions))
            .distinct()
        )
        
        return self.session.exec(statement).all()

    def upsert_embedding(self, schedule_id: str, embedding: list) -> None:
        """儲存或更新行程的 embedding 向量"""
        from sqlalchemy import text
        vec_literal = "[" + ",".join(str(x) for x in embedding) + "]"
        self.session.execute(
            text(f"""
                INSERT INTO schedule_management.schedule_embedding (schedule_id, embedding, updated_at)
                VALUES (:sid, '{vec_literal}'::vector, NOW())
                ON CONFLICT (schedule_id) DO UPDATE
                SET embedding = '{vec_literal}'::vector, updated_at = NOW()
            """),
            {"sid": schedule_id}
        )
        self.session.commit()

    def delete_embedding(self, schedule_id: str) -> None:
        """刪除行程的 embedding"""
        from sqlalchemy import text
        self.session.execute(
            text("DELETE FROM schedule_management.schedule_embedding WHERE schedule_id = :sid"),
            {"sid": schedule_id}
        )
        self.session.commit()

    def semantic_search(self, user_id: str, query_embedding: list,
                        top_k: int = 10) -> List[tuple]:
        """
        用 cosine similarity 搜尋用戶的行程。
        回傳 List[(Schedule, similarity_score)] 依相似度降序排列。
        """
        from sqlalchemy import text
        # 向量直接內嵌 SQL（numpy floats，非用戶輸入，無 injection 風險）
        # 避免 SQLAlchemy text() 將 `:emb::vector` 中的 `::` 誤解析為參數前綴
        vec_literal = "[" + ",".join(str(x) for x in query_embedding) + "]"
        rows = self.session.execute(
            text(f"""
                SELECT s.schedule_id,
                       1 - (se.embedding <=> '{vec_literal}'::vector) AS similarity
                FROM schedule_management.schedule s
                JOIN schedule_management.schedule_embedding se
                  ON s.schedule_id = se.schedule_id
                WHERE s.user_id = :user_id
                ORDER BY se.embedding <=> '{vec_literal}'::vector
                LIMIT :top_k
            """),
            {"user_id": user_id, "top_k": top_k}
        ).fetchall()

        id_scores = [(row.schedule_id, float(row.similarity)) for row in rows]
        if not id_scores:
            return []
        schedules = self.session.exec(
            select(Schedule).where(Schedule.schedule_id.in_([sid for sid, _ in id_scores]))
        ).all()
        by_id = {s.schedule_id: s for s in schedules}
        return [(by_id[sid], score) for sid, score in id_scores if sid in by_id]

    # ── Contact Embedding ────────────────────────────────────────────────────

    def upsert_contact_embedding(self, contact_id: int, user_id: str, embedding: list) -> None:
        from sqlalchemy import text
        vec_literal = "[" + ",".join(str(x) for x in embedding) + "]"
        self.session.execute(
            text(f"""
                INSERT INTO schedule_management.contact_embedding (contact_id, user_id, embedding, updated_at)
                VALUES (:cid, :uid, '{vec_literal}'::vector, NOW())
                ON CONFLICT (contact_id) DO UPDATE
                SET embedding = '{vec_literal}'::vector, updated_at = NOW()
            """),
            {"cid": contact_id, "uid": user_id}
        )
        self.session.commit()

    def semantic_search_contacts(self, user_id: str, query_embedding: list,
                                  top_k: int = 3, min_similarity: float = 0.4) -> list:
        """語意搜尋聯絡人，回傳 [{id, nick_name, comment, similarity}]"""
        from sqlalchemy import text
        vec_literal = "[" + ",".join(str(x) for x in query_embedding) + "]"
        rows = self.session.execute(
            text(f"""
                SELECT c.id, c.nick_name, c.comment,
                       1 - (ce.embedding <=> '{vec_literal}'::vector) AS similarity
                FROM schedule_management.contact c
                JOIN schedule_management.contact_embedding ce ON c.id = ce.contact_id
                WHERE c.user_id = :user_id
                  AND 1 - (ce.embedding <=> '{vec_literal}'::vector) >= :min_sim
                ORDER BY ce.embedding <=> '{vec_literal}'::vector
                LIMIT :top_k
            """),
            {"user_id": user_id, "top_k": top_k, "min_sim": min_similarity}
        ).fetchall()
        return [
            {"id": r.id, "nick_name": r.nick_name or "", "comment": r.comment or "",
             "similarity": round(float(r.similarity), 4)}
            for r in rows
        ]

    def find_duplicate_contacts(self, user_id: str, nick_names: list[str]) -> dict:
        """給定名字列表，回傳有重複的 {nick_name: [{id, comment, phone}]} 字典"""
        from sqlalchemy import text
        if not nick_names:
            return {}
        placeholders = ",".join(f":n{i}" for i in range(len(nick_names)))
        params = {"user_id": user_id, **{f"n{i}": n for i, n in enumerate(nick_names)}}
        rows = self.session.execute(
            text(f"""
                SELECT id, nick_name, comment, phone
                FROM schedule_management.contact
                WHERE user_id = :user_id AND nick_name IN ({placeholders})
                ORDER BY nick_name, id
            """),
            params
        ).fetchall()
        result: dict = {}
        for r in rows:
            result.setdefault(r.nick_name, []).append({
                "id": r.id,
                "comment": r.comment or "",
                "phone": (r.phone or "")[-4:] if r.phone else "",
            })
        return {k: v for k, v in result.items() if len(v) > 1}

    # ── User Memory ──────────────────────────────────────────────────────────

    def save_user_memory(self, user_id: str, content: str,
                         memory_type: str, embedding: list) -> None:
        from sqlalchemy import text
        vec_literal = "[" + ",".join(str(x) for x in embedding) + "]"
        self.session.execute(
            text(f"""
                INSERT INTO schedule_management.user_memory (user_id, content, memory_type, embedding)
                VALUES (:uid, :content, :mtype, '{vec_literal}'::vector)
            """),
            {"uid": user_id, "content": content, "mtype": memory_type}
        )
        self.session.commit()

    def search_user_memory(self, user_id: str, query_embedding: list,
                            top_k: int = 3, min_similarity: float = 0.45) -> list:
        """搜尋與當前問題最相關的用戶記憶片段"""
        from sqlalchemy import text
        vec_literal = "[" + ",".join(str(x) for x in query_embedding) + "]"
        rows = self.session.execute(
            text(f"""
                SELECT content, memory_type,
                       1 - (embedding <=> '{vec_literal}'::vector) AS similarity
                FROM schedule_management.user_memory
                WHERE user_id = :user_id AND embedding IS NOT NULL
                  AND 1 - (embedding <=> '{vec_literal}'::vector) >= :min_sim
                ORDER BY embedding <=> '{vec_literal}'::vector
                LIMIT :top_k
            """),
            {"user_id": user_id, "top_k": top_k, "min_sim": min_similarity}
        ).fetchall()
        return [
            {"content": r.content, "type": r.memory_type,
             "similarity": round(float(r.similarity), 4)}
            for r in rows
        ]

    def find_overlapping(self, user_id: str, start_time: datetime, end_time: datetime, exclude_schedule_id: Optional[str] = None) -> List[Schedule]:
        """
        Find schedules that overlap with the given time range for the user.
        Overlapping logic: (StartA < EndB) and (EndA > StartB)
        
        NOTE: The database columns meeting_start_time and meeting_end_time seem to be VARCHAR
        in some environments, causing comparison errors. We cast them to TIMESTAMP here.
        """
        from sqlalchemy import func, TIMESTAMP
        
        # Ensure we are comparing 'like with like'. 
        # If DB is varchar, we cast DB col to timestamp.
        statement = (
            select(Schedule)
            .where(Schedule.user_id == user_id)
            .where(Schedule.status != Status.CANCEL.value)  # Ignore cancelled ("CL")
            .where(func.cast(Schedule.meeting_start_time, TIMESTAMP) < end_time)
            .where(func.cast(Schedule.meeting_end_time, TIMESTAMP) > start_time)
        )
        
        if exclude_schedule_id:
            statement = statement.where(Schedule.schedule_id != exclude_schedule_id)
            
        return self.session.exec(statement).all()
