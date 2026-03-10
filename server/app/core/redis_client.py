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
            password=os.getenv("REDIS_PASSWORD"),
            ssl=os.getenv("REDIS_TLS", "false").lower() == "true",
            decode_responses=True
        )
    
    def store_token(self, user_id: str, token: str, expire_seconds: int = 604800):
        """
        儲存 JWT Token 到 Redis，並覆蓋舊的 token
        key 格式: jwt:{user_id}
        TTL: 7 天（604800 秒）
        """
        key = f"jwt:{user_id}"
        return self.client.setex(key, expire_seconds, token)
    
    def validate_token(self, user_id: str, token: str) -> bool:
        """驗證 Token 是否與存在於 Redis 的最新 Token 相符"""
        # 1. 檢查精確匹配
        key = f"jwt:{user_id}"
        stored_token = self.client.get(key)
        if stored_token == token:
            return True
            
        # 2. 檢查帶有 session_id 後綴的 key (例如 jwt:user_id:session_id)
        pattern = f"jwt:{user_id}:*"
        for k in self.client.scan_iter(match=pattern):
            if self.client.get(k) == token:
                return True
                
        return False
    
    def revoke_token(self, user_id: str, token: str):
        """登出時刪除 Token（如果傳來的 Token 與目前的 Token 符合才刪除）"""
        # 1. 檢查精確匹配
        key = f"jwt:{user_id}"
        stored_token = self.client.get(key)
        if stored_token == token:
            self.client.delete(key)
            return
            
        # 2. 檢查帶有 session_id 後綴的 key (例如 jwt:user_id:session_id)
        pattern = f"jwt:{user_id}:*"
        for k in self.client.scan_iter(match=pattern):
            if self.client.get(k) == token:
                self.client.delete(k)
                break
    
    def delete_all_user_tokens(self, user_id: str):
        """刪除用戶的 Token（強制登出）"""
        # 1. 刪除精確匹配的 key
        key = f"jwt:{user_id}"
        self.client.delete(key)
        
        # 2. 刪除所有帶有 session_id 後綴的 key
        pattern = f"jwt:{user_id}:*"
        for k in self.client.scan_iter(match=pattern):
            self.client.delete(k)

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
