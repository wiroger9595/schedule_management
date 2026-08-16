"""
訂閱方案（RevenueCat）+ 用戶自帶 AI key（BYOK）。

方案規則
────────
free : 每月 FREE_MONTHLY_AI_QUOTA 次 AI 對話，走我們的 API key
pro  : 自己填 OpenAI 相容端點的 key，不計次

plan 的真實來源是 RevenueCat：webhook 即時推、/sync 主動對帳（webhook 漏送時的保險）。
"""
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import requests
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ...core.crypto import decrypt, encrypt, mask
from ...db.database import get_session
from ...models.user import User
from ...repositories.user_repository import UserRepository
from ...services import ai_quota_service, byok_service
from .auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

REVENUECAT_WEBHOOK_AUTH = os.getenv("REVENUECAT_WEBHOOK_AUTH")
REVENUECAT_SECRET_KEY = os.getenv("REVENUECAT_SECRET_KEY")
PRO_ENTITLEMENT = os.getenv("REVENUECAT_ENTITLEMENT_ID", "pro")

# 授予 pro 的事件。CANCELLATION 不在裡面 —— 那只代表關掉自動續訂，
# 訂閱到期前權益仍然有效，真正要收回是 EXPIRATION。
GRANT_EVENTS = {
    "INITIAL_PURCHASE", "RENEWAL", "UNCANCELLATION", "NON_RENEWING_PURCHASE",
    "PRODUCT_CHANGE", "SUBSCRIPTION_EXTENDED", "TEMPORARY_ENTITLEMENT_GRANT",
}
REVOKE_EVENTS = {"EXPIRATION", "SUBSCRIPTION_PAUSED"}


class AiKeyUpdate(BaseModel):
    base_url: str
    api_key: str
    model: str


def _ms_to_datetime(ms: Optional[int]) -> Optional[datetime]:
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def _parse_rc_date(raw: Optional[str]) -> Optional[datetime]:
    """
    RevenueCat REST 的日期字串。格式可能帶毫秒也可能不帶
    （2026-08-16T12:00:00Z / 2026-08-16T12:00:00.000Z），兩種都要吃。
    """
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        logger.warning(f"[billing] 無法解析 RevenueCat 日期：{raw}")
        return None


def _fetch_entitlement(app_user_id: str) -> tuple:
    """
    跟 RevenueCat REST 問這個帳號的 pro 權益，回傳 (是否有效, 到期時間)。
    連不上就往外丟，讓呼叫端決定要不要當成失敗。
    """
    resp = requests.get(
        f"https://api.revenuecat.com/v1/subscribers/{app_user_id}",
        headers={"Authorization": f"Bearer {REVENUECAT_SECRET_KEY}"},
        timeout=10,
    )
    resp.raise_for_status()
    ent = resp.json().get("subscriber", {}).get("entitlements", {}).get(PRO_ENTITLEMENT)
    if not ent:
        return False, None

    expires_at = _parse_rc_date(ent.get("expires_date"))
    if expires_at is None:
        return True, None  # 沒有到期日 = 永久解鎖（買斷型商品）
    return expires_at > datetime.now(timezone.utc), expires_at


def _apply_plan(session: Session, app_user_id: str, active: bool, expires_at: Optional[datetime]):
    """把權益狀態寫回 users，回傳更新後的 user（找不到帳號回 None）。"""
    repo = UserRepository(session)
    user = repo.get_by_id(app_user_id)
    if not user:
        return None
    user.plan = "pro" if active else "free"
    user.plan_expires_at = expires_at if active else None
    user.updated_at = datetime.now()
    repo.update(user)
    return user


def _ai_key_info(user: User) -> dict:
    return {
        "configured": bool(user.ai_api_key_enc),
        "base_url": user.ai_base_url,
        "model": user.ai_model,
        "api_key_masked": mask(decrypt(user.ai_api_key_enc)),
    }


# ─── 方案狀態 ─────────────────────────────────────────────────────────────────

@router.get("/status")
def get_billing_status(
    current_user: User = Depends(get_current_user),
):
    """前端開 app / 進設定頁時打，拿方案 + 本月剩餘次數 + BYOK 設定狀態。"""
    return {**ai_quota_service.get_status(current_user), "ai_key": _ai_key_info(current_user)}


@router.post("/sync")
def sync_subscription(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    主動跟 RevenueCat 對帳。前端在購買完成、restore、或開 app 時呼叫，
    不必等 webhook 才生效（webhook 也可能漏送）。
    """
    if not REVENUECAT_SECRET_KEY:
        raise HTTPException(status_code=503, detail="訂閱服務尚未設定")

    try:
        active, expires_at = _fetch_entitlement(current_user.user_id)
    except Exception as e:
        logger.warning(f"[billing] RevenueCat sync failed: {str(e)[:200]}")
        raise HTTPException(status_code=502, detail="無法連線訂閱服務，請稍後再試")

    user = _apply_plan(session, current_user.user_id, active, expires_at)
    return {**ai_quota_service.get_status(user), "ai_key": _ai_key_info(user)}


@router.post("/webhook")
async def revenuecat_webhook(
    payload: dict,
    authorization: Optional[str] = Header(default=None),
    session: Session = Depends(get_session),
):
    """
    RevenueCat webhook。在 RevenueCat 後台把 Authorization header 設成
    REVENUECAT_WEBHOOK_AUTH 的值，不符就拒絕。
    """
    if not REVENUECAT_WEBHOOK_AUTH:
        logger.error("[billing] REVENUECAT_WEBHOOK_AUTH 未設定，拒絕 webhook")
        raise HTTPException(status_code=503, detail="webhook not configured")
    if authorization != REVENUECAT_WEBHOOK_AUTH:
        raise HTTPException(status_code=401, detail="invalid webhook auth")

    event = payload.get("event") or {}
    event_type = event.get("type", "")
    app_user_id = event.get("app_user_id")

    # TRANSFER 沒有 app_user_id，而是 transferred_from / transferred_to。
    # 不處理的話舊帳號會一直留著 pro，變成一份訂閱兩個帳號在用。
    if event_type == "TRANSFER":
        return _handle_transfer(event, session)

    if not app_user_id:
        return {"ok": True, "skipped": "no app_user_id"}

    # entitlement_ids 有值時才檢查，某些事件不帶這個欄位
    entitlement_ids = event.get("entitlement_ids")
    if entitlement_ids and PRO_ENTITLEMENT not in entitlement_ids:
        return {"ok": True, "skipped": f"entitlement {entitlement_ids} not handled"}

    if event_type in GRANT_EVENTS:
        active, expires_at = True, _ms_to_datetime(event.get("expiration_at_ms"))
    elif event_type in REVOKE_EVENTS:
        active, expires_at = False, None
    else:
        # CANCELLATION / BILLING_ISSUE / TEST 等：不動權益，等 EXPIRATION 再收
        logger.info(f"[billing] webhook {event_type} for {app_user_id}: no plan change")
        return {"ok": True, "event": event_type}

    user = _apply_plan(session, app_user_id, active, expires_at)
    if not user:
        # 匿名 ID 或已刪除的帳號，回 200 避免 RevenueCat 一直重送
        logger.info(f"[billing] webhook {event_type}: user {app_user_id} not found")
        return {"ok": True, "skipped": "user not found"}

    logger.info(f"[billing] webhook {event_type}: {app_user_id} → plan={user.plan}")
    return {"ok": True, "event": event_type, "plan": user.plan}


def _handle_transfer(event: dict, session: Session) -> dict:
    """
    訂閱在帳號之間移轉：來源帳號一律降回 free；目的帳號因為事件本身不帶到期日，
    改用 REST 查一次真實權益（沒設 secret key 就等前端的 /billing/sync 補）。
    """
    moved_from = event.get("transferred_from") or []
    moved_to = event.get("transferred_to") or []

    for user_id in moved_from:
        if _apply_plan(session, user_id, active=False, expires_at=None):
            logger.info(f"[billing] transfer: {user_id} → free")

    for user_id in moved_to:
        if not REVENUECAT_SECRET_KEY:
            logger.warning(f"[billing] transfer: 無法查 {user_id} 的權益（未設 REVENUECAT_SECRET_KEY）")
            continue
        try:
            active, expires_at = _fetch_entitlement(user_id)
        except Exception as e:
            logger.warning(f"[billing] transfer: 查 {user_id} 權益失敗 {str(e)[:120]}")
            continue
        if _apply_plan(session, user_id, active, expires_at):
            logger.info(f"[billing] transfer: {user_id} → {'pro' if active else 'free'}")

    return {"ok": True, "event": "TRANSFER", "from": moved_from, "to": moved_to}


# ─── BYOK：用戶自帶 AI key ────────────────────────────────────────────────────

@router.put("/ai-key")
def set_ai_key(
    data: AiKeyUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    設定自己的 OpenAI 相容端點。只有 pro 能設 —— 免費版設了也不會生效，
    不如在這裡就擋掉，避免用戶以為設好了卻還在扣額度。
    """
    if not ai_quota_service.is_pro(current_user):
        raise HTTPException(status_code=403, detail="需要訂閱後才能使用自己的 AI 服務")

    try:
        base_url = byok_service.normalize_base_url(data.base_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    model = (data.model or "").strip()
    api_key = (data.api_key or "").strip()
    if not model:
        raise HTTPException(status_code=400, detail="請填寫模型名稱")
    if not api_key:
        raise HTTPException(status_code=400, detail="請填寫 API key")

    # 加密金鑰沒設好時先擋下來，不要等驗證完才 500（那樣還白打一次用戶的 API）
    try:
        encrypted_key = encrypt(api_key)
    except RuntimeError as e:
        logger.error(f"[billing] 無法加密用戶 API key：{e}")
        raise HTTPException(status_code=503, detail="伺服器尚未設定金鑰加密，請聯絡管理員")

    ok, err = byok_service.verify_credentials(base_url, api_key, model)
    if not ok:
        raise HTTPException(status_code=400, detail=err)

    repo = UserRepository(session)
    user = repo.get_by_id(current_user.user_id)
    user.ai_base_url = base_url
    user.ai_model = model
    user.ai_api_key_enc = encrypted_key
    user.updated_at = datetime.now()
    repo.update(user)

    return {**ai_quota_service.get_status(user), "ai_key": _ai_key_info(user)}


@router.delete("/ai-key")
def delete_ai_key(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """移除自己的 key，之後回到免費額度流程。"""
    repo = UserRepository(session)
    user = repo.get_by_id(current_user.user_id)
    user.ai_base_url = None
    user.ai_model = None
    user.ai_api_key_enc = None
    user.updated_at = datetime.now()
    repo.update(user)
    return {**ai_quota_service.get_status(user), "ai_key": _ai_key_info(user)}
