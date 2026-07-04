"""
MemoryService — 從成功的行程操作中提取用戶偏好記憶並儲存。
規則式提取，不額外呼叫 AI，避免增加延遲與成本。
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
import logging
logger = logging.getLogger(__name__)


class MemoryService:

    @staticmethod
    def extract_and_save(
        user_id: str,
        schedule_data: dict,
        intent: str,        # 'create' | 'edit'
        contact_name: str,  # 空字串表示無聯絡人
        session,
    ) -> None:
        """
        從成功的行程建立/更新中提取偏好記憶並儲存到 user_memory 表。
        失敗不影響主流程。
        """
        try:
            from ..repositories.schedule_repository import ScheduleRepository
            from ..services.embedding_service import EmbeddingService

            repo = ScheduleRepository(session)
            memories: list[tuple[str, str]] = []  # (content, memory_type)

            title = schedule_data.get("title") or schedule_data.get("schedule_title", "")
            location = (schedule_data.get("location") or
                        schedule_data.get("meeting_location", ""))
            start_time_raw = (schedule_data.get("start_time") or
                              schedule_data.get("meeting_start_time"))

            # ── 地點偏好 ──────────────────────────────────────────────────────
            if location:
                memories.append((
                    f"用戶偏好的行程地點：{location}",
                    "location_preference"
                ))
                if contact_name:
                    memories.append((
                        f"用戶與「{contact_name}」的行程通常在「{location}」",
                        "contact_location"
                    ))

            # ── 時間偏好 ──────────────────────────────────────────────────────
            if start_time_raw:
                try:
                    dt = (datetime.fromisoformat(str(start_time_raw))
                          if isinstance(start_time_raw, str) else start_time_raw)
                    hour = dt.hour
                    if 6 <= hour < 12:
                        period = "上午"
                    elif 12 <= hour < 14:
                        period = "中午"
                    elif 14 <= hour < 18:
                        period = "下午"
                    elif 18 <= hour < 22:
                        period = "晚上"
                    else:
                        period = "深夜"
                    if title:
                        memories.append((
                            f"用戶偏好在{period}安排「{title}」",
                            "time_preference"
                        ))
                except Exception:
                    pass

            # ── 聯絡人關聯 ───────────────────────────────────────────────────
            if contact_name and title:
                memories.append((
                    f"用戶有與「{contact_name}」相關的行程：{title}",
                    "contact_schedule"
                ))

            # ── 儲存（批次 embed 節省時間）───────────────────────────────────
            if memories:
                texts = [m[0] for m in memories]
                embeddings = EmbeddingService.embed_batch(texts)
                for (content, mtype), emb in zip(memories, embeddings):
                    try:
                        repo.save_user_memory(user_id, content, mtype, emb)
                    except Exception as _e:
                        try:
                            session.rollback()
                        except Exception:
                            pass
                        logger.info(f"[memory] save failed for '{content[:30]}': {_e}")

        except Exception as e:
            logger.info(f"[MemoryService] extract_and_save error (non-critical): {e}")
