"""
一次性腳本：為所有用戶的所有行程 + 聯絡人補建 embedding。
在 server/ 目錄下執行：python reindex_all_embeddings.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.db.database import engine
from sqlmodel import Session, select

# Import all models first so SQLAlchemy mapper can resolve all relationships
import app.models.user        # noqa: F401
import app.models.contact     # noqa: F401
import app.models.attend      # noqa: F401
from app.models.schedule import Schedule
from app.models.contact import Contact
from app.repositories.schedule_repository import ScheduleRepository
from app.services.embedding_service import EmbeddingService


def reindex_schedules(session: Session) -> dict:
    repo = ScheduleRepository(session)
    schedules = session.exec(select(Schedule)).all()
    total = len(schedules)
    print(f"\n[行程] 共 {total} 筆，開始建立豐富化 embedding...")

    success = failed = skipped = 0
    for i, s in enumerate(schedules, 1):
        try:
            title = s.title or ""
            location = s.meeting_location or ""
            desc = s.description or ""
            if not title and not location and not desc:
                skipped += 1
                continue

            # 查詢聯絡人姓名
            contact_name = ""
            if s.contact_id:
                c = session.get(Contact, s.contact_id)
                if c:
                    contact_name = c.nick_name or ""

            emb = EmbeddingService.embed_schedule(
                title, location, desc,
                contact_name=contact_name,
                start_time=s.meeting_start_time,
            )
            repo.upsert_embedding(s.schedule_id, emb)
            success += 1

            if i % 10 == 0:
                print(f"  進度: {i}/{total} (成功={success}, 失敗={failed}, 跳過={skipped})")

        except Exception as e:
            print(f"  [失敗] schedule_id={s.schedule_id} title={s.title!r}: {e}")
            try:
                session.rollback()
            except Exception:
                pass
            failed += 1

    print(f"[行程] 完成：總計={total}, 成功={success}, 失敗={failed}, 跳過={skipped}")
    return {"total": total, "success": success, "failed": failed}


def reindex_contacts(session: Session) -> dict:
    repo = ScheduleRepository(session)
    contacts = session.exec(select(Contact)).all()
    total = len(contacts)
    print(f"\n[聯絡人] 共 {total} 筆，開始建立 embedding...")

    success = failed = skipped = 0
    for i, c in enumerate(contacts, 1):
        try:
            if not c.nick_name:
                skipped += 1
                continue

            emb = EmbeddingService.embed_contact(
                c.nick_name or "",
                c.comment or "",
            )
            repo.upsert_contact_embedding(c.id, c.user_id, emb)
            success += 1

            if i % 20 == 0:
                print(f"  進度: {i}/{total} (成功={success}, 失敗={failed}, 跳過={skipped})")

        except Exception as e:
            print(f"  [失敗] contact_id={c.id} nick_name={c.nick_name!r}: {e}")
            try:
                session.rollback()
            except Exception:
                pass
            failed += 1

    print(f"[聯絡人] 完成：總計={total}, 成功={success}, 失敗={failed}, 跳過={skipped}")
    return {"total": total, "success": success, "failed": failed}


if __name__ == "__main__":
    with Session(engine) as session:
        s_result = reindex_schedules(session)
        c_result = reindex_contacts(session)

    print(f"\n{'='*50}")
    print(f"全部完成！")
    print(f"  行程：{s_result['success']}/{s_result['total']} 成功")
    print(f"  聯絡人：{c_result['success']}/{c_result['total']} 成功")
