from datetime import datetime, timedelta
from typing import Optional, Union, Any
from jose import jwt
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

# JWT Config
# ⚠️ TODO(security, 上線前必修):
#   1. 這裡讀的是 JWT_SECRET_KEY，但 .env 裡設定的 key 名是 SECRET_KEY
#      → 目前實際上正在用下面這個公開的 fallback 字串簽 token，任何人都可偽造。
#      修法：統一 env 名稱，且沒設定時直接 raise（fail fast），不要給預設值。
#      注意：改 key 會讓所有既有 token 失效，需要用戶重新登入。
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-it-in-production")
ALGORITHM = "HS256"
# ⚠️ TODO(security, 上線前必修):
#   2. token 有效期 7 天且無 refresh/撤銷機制，token 被竊取後 7 天內無法作廢。
#      上線前縮短（例如 1 天）並加 refresh token。
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

def _encode(password: str) -> bytes:
    # bcrypt limits to 72 bytes — truncate at byte boundary
    return password.encode("utf-8")[:72]

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(_encode(plain_password), hashed_password.encode("utf-8"))

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(_encode(password), bcrypt.gensalt()).decode("utf-8")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
