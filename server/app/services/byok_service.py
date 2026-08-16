"""
BYOK（Bring Your Own Key）— pro 用戶自帶的 OpenAI 相容端點。

支援任意端點意味著 base_url 是用戶輸入的，會被我們的伺服器主動連線，
所以存進 DB 之前一定要擋掉內網位址（SSRF），並實際打一次確認 key 有效。
"""
from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Optional, Tuple
from urllib.parse import urlparse

from openai import OpenAI

from ..core.crypto import decrypt
from ..models.user import User

logger = logging.getLogger(__name__)

# 驗證時打一次真的 completion，模型冷啟動有時很慢，但也不能讓 API 卡太久
VERIFY_TIMEOUT_SECONDS = 20.0


def normalize_base_url(raw: str) -> str:
    """
    正規化並檢查 base_url，不合法時 raise ValueError（訊息直接給用戶看）。
    回傳去掉結尾斜線的 URL。
    """
    url = (raw or "").strip().rstrip("/")
    if not url:
        raise ValueError("請填寫 API 位址")

    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("API 位址必須是 https 開頭")
    if not parsed.hostname:
        raise ValueError("API 位址格式不正確")

    _reject_internal_host(parsed.hostname)
    return url


def _reject_internal_host(hostname: str):
    """把 hostname 解析成 IP，落在內網 / loopback / 保留網段就拒絕。"""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError(f"無法解析網域：{hostname}")

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise ValueError("不接受指向內部網路的 API 位址")


def verify_credentials(base_url: str, api_key: str, model: str) -> Tuple[bool, Optional[str]]:
    """
    實際呼叫一次，確認 key / model 組合可用。回傳 (成功, 錯誤訊息)。
    存進 DB 前一定要跑這個，否則用戶要等到聊天時才發現填錯。
    """
    try:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=VERIFY_TIMEOUT_SECONDS)
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1,
        )
        return True, None
    except Exception as e:
        err = str(e)
        low = err.lower()
        if "401" in err or "invalid_api_key" in low or "unauthorized" in low:
            return False, "API key 無效"
        if "404" in err or "model_not_found" in low or "does not exist" in low:
            return False, f"找不到模型 {model}，請確認模型名稱"
        if "429" in err:
            return False, "這個 key 目前已達供應商的速率上限，請稍後再試"
        logger.info(f"[BYOK] verify failed: {err[:200]}")
        return False, f"連線失敗：{err[:100]}"


def build_provider(user: User) -> Optional[tuple]:
    """
    組出 ai_service 用的 provider tuple (client, model, label)。
    key 解不開（例如加密 secret 被換過）就回 None，呼叫端退回免費額度流程。
    """
    api_key = decrypt(user.ai_api_key_enc)
    if not api_key or not user.ai_base_url or not user.ai_model:
        return None
    return (
        OpenAI(api_key=api_key, base_url=user.ai_base_url),
        user.ai_model,
        f"BYOK/{user.ai_model}",
    )
