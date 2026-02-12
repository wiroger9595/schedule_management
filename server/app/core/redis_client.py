import redis
from typing import Optional
import os
import hashlib
from dotenv import load_dotenv

load_dotenv()

class RedisClient:
    def __init__(self):
        self.client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            decode_responses=True
        )
    
    def store_token(self, user_id: str, token: str, expire_seconds: int = 604800):
        """
        儲存 JWT Token 到 Redis
        key 格式: jwt:{user_id}:{token_hash}
        TTL: 7 天（604800 秒）
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        key = f"jwt:{user_id}:{token_hash}"
        return self.client.setex(key, expire_seconds, token)
    
    def validate_token(self, user_id: str, token: str) -> bool:
        """驗證 Token 是否存在於 Redis"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        key = f"jwt:{user_id}:{token_hash}"
        return self.client.exists(key) > 0
    
    def revoke_token(self, user_id: str, token: str):
        """登出時刪除 Token"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        key = f"jwt:{user_id}:{token_hash}"
        self.client.delete(key)
    
    def delete_all_user_tokens(self, user_id: str):
        """刪除用戶的所有 Token（例如：強制登出所有裝置）"""
        pattern = f"jwt:{user_id}:*"
        for key in self.client.scan_iter(match=pattern):
            self.client.delete(key)

    def set_reset_code(self, email: str, code: str, expire_seconds: int = 600):
        """儲存密碼重置驗證碼 (預設 10 分鐘)"""
        key = f"reset:{email}"
        self.client.setex(key, expire_seconds, code)

    def get_reset_code(self, email: str) -> Optional[str]:
        """獲取密碼重置驗證碼"""
        key = f"reset:{email}"
        return self.client.get(key)

    def delete_reset_code(self, email: str):
        """刪除密碼重置驗證碼"""
        key = f"reset:{email}"
        self.client.delete(key)

redis_client = RedisClient()
