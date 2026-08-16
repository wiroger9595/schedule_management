"""
對稱加密工具 — 目前只用在「用戶自帶的 AI API key」。

key 是用戶的憑證，不是我們的，所以 DB 只存密文，任何 API 回應都只回遮罩字串。
"""
import base64
import hashlib
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

load_dotenv()

_fernet_cache: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    global _fernet_cache
    if _fernet_cache is not None:
        return _fernet_cache

    # 專用 secret 優先；沒設就退回 JWT secret，避免多一個部署必填變數就整個功能掛掉
    secret = os.getenv("AI_KEY_ENC_SECRET") or os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
    if not secret:
        raise RuntimeError("需要設定 AI_KEY_ENC_SECRET（或 JWT_SECRET_KEY）才能加密用戶 API key")
    # auth.py 的公開 fallback 字串在 repo 裡人人看得到，拿它當加密金鑰等於沒加密
    if secret == "your-secret-key-change-it-in-production":
        raise RuntimeError("AI_KEY_ENC_SECRET 不能用預設值，請設一把獨立的隨機字串")

    # Fernet 要 32 bytes urlsafe base64，任意長度的 secret 先過 sha256 正規化
    _fernet_cache = Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))
    return _fernet_cache


def encrypt(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: Optional[str]) -> Optional[str]:
    """
    解不開就回 None（例如 secret 被換過），呼叫端當作「用戶沒設 key」處理，
    讓他重填一次即可，不要讓整條 chat 路徑爆掉。
    """
    if not ciphertext:
        return None
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, ValueError, RuntimeError):
        return None


def mask(plaintext: Optional[str]) -> Optional[str]:
    """回給前端顯示用：sk-abc...wxyz"""
    if not plaintext:
        return None
    if len(plaintext) <= 12:
        return plaintext[:2] + "***"
    return f"{plaintext[:6]}...{plaintext[-4:]}"
