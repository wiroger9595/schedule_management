"""
AI 額度與訂閱方案判斷 — chat 端點呼叫 AI 前的唯一守門員。

規則
────
- free：每月 FREE_MONTHLY_AI_QUOTA 次（預設 5），走我們自己的 API key
- pro ：用戶自帶 key（BYOK），不計次；沒設 key 時仍吃 free 額度
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from ..core.redis_client import redis_client
from ..models.user import User

logger = logging.getLogger(__name__)

FREE_MONTHLY_QUOTA = int(os.getenv("FREE_MONTHLY_AI_QUOTA", "5"))


def is_pro(user: User) -> bool:
    """plan 是 pro 且未過期。到期時間由 RevenueCat webhook 維護。"""
    if (user.plan or "free") != "pro":
        return False
    expires = user.plan_expires_at
    if expires is None:
        return True
    # DB 欄位是 TIMESTAMPTZ，但舊資料可能是 naive，統一補上 UTC 再比
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires > datetime.now(timezone.utc)


def has_own_key(user: User) -> bool:
    return bool(user.ai_api_key_enc and user.ai_base_url and user.ai_model)


def uses_own_key(user: User) -> bool:
    """只有 pro 且真的設好 key 才走自己的額度。"""
    return is_pro(user) and has_own_key(user)


def get_status(user: User) -> dict:
    """給 GET /billing/status 和前端額度顯示用。"""
    pro = is_pro(user)
    own_key = uses_own_key(user)
    used = redis_client.get_monthly_ai_usage(user.user_id)
    return {
        "plan": "pro" if pro else "free",
        "plan_expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at else None,
        "using_own_key": own_key,
        "monthly_limit": None if own_key else FREE_MONTHLY_QUOTA,
        "monthly_used": used,
        "monthly_remaining": None if own_key else max(0, FREE_MONTHLY_QUOTA - used),
    }


def resolve_for_chat(user: User) -> dict:
    """
    chat 端點呼叫 AI 前的一站式判斷，回傳：
      allowed       – 能不能打這次 AI
      using_own_key – 是否走用戶自己的端點（不計次）
      providers     – 傳給 ai_service.process_conversation 的 provider list
      remaining     – 本月剩餘次數（BYOK 時為 None）

    這裡只檢查不扣點，扣點在 AI 真的回應之後（見 consume）。
    """
    providers = None
    if uses_own_key(user):
        from .byok_service import build_provider
        provider = build_provider(user)
        if provider:
            providers = [provider]
        else:
            # key 解不開（加密 secret 換過）→ 當作沒設，退回免費額度
            logger.warning(f"[quota] user {user.user_id} BYOK key unusable, falling back to free quota")

    if providers:
        return {"allowed": True, "using_own_key": True, "providers": providers,
                "remaining": None, "limit": None}

    used = redis_client.get_monthly_ai_usage(user.user_id)
    return {"allowed": used < FREE_MONTHLY_QUOTA, "using_own_key": False, "providers": None,
            "remaining": max(0, FREE_MONTHLY_QUOTA - used), "limit": FREE_MONTHLY_QUOTA}


def remaining(user: User) -> int:
    return max(0, FREE_MONTHLY_QUOTA - redis_client.get_monthly_ai_usage(user.user_id))


def consume(user: User, using_own_key: bool) -> Optional[int]:
    """AI 成功回應後才扣，回傳本月剩餘次數（BYOK 為 None）。"""
    if using_own_key:
        return None
    used = redis_client.incr_monthly_ai_usage(user.user_id)
    return max(0, FREE_MONTHLY_QUOTA - used)
