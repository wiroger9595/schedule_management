"""auth.py 核心邏輯：密碼雜湊、JWT 簽發/驗證。純邏輯，不需 DB。"""
from datetime import timedelta

from jose import jwt

from app.core.auth import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    get_password_hash,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = get_password_hash("my-secret-密碼123")
    assert verify_password("my-secret-密碼123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_password_hash_is_salted():
    # 同一密碼兩次雜湊結果不同（有 salt）
    assert get_password_hash("same") != get_password_hash("same")


def test_password_over_72_bytes_truncated_consistently():
    # bcrypt 上限 72 bytes——超長密碼要能一致地驗證，不能 crash
    long_pw = "中" * 40  # 40 * 3 bytes = 120 bytes
    hashed = get_password_hash(long_pw)
    assert verify_password(long_pw, hashed)


def test_token_roundtrip():
    token = create_access_token({"sub": "user-123"})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "user-123"
    assert "exp" in payload


def test_expired_token_rejected():
    token = create_access_token({"sub": "u"}, expires_delta=timedelta(seconds=-10))
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert False, "過期 token 不應通過驗證"
    except jwt.ExpiredSignatureError:
        pass


def test_tampered_token_rejected():
    token = create_access_token({"sub": "u"})
    try:
        jwt.decode(token, "wrong-secret", algorithms=[ALGORITHM])
        assert False, "錯誤 secret 簽的 token 不應通過"
    except jwt.JWTError:
        pass
