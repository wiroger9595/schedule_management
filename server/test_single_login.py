import os
from dotenv import load_dotenv

# Setup minimal env for RedisClient
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ["REDIS_DB"] = "0"

from app.core.redis_client import redis_client

def test_single_device_login():
    user_id = "test_user_123"
    token_device_A = "header.payloadA.signature"
    token_device_B = "header.payloadB.signature"
    
    # 1. Device A logs in
    redis_client.store_token(user_id, token_device_A)
    print(f"Device A logged in with token: {token_device_A}")
    
    # Verify Device A is valid
    is_valid_A = redis_client.validate_token(user_id, token_device_A)
    print(f"Device A token valid? {is_valid_A} (Expected: True)")
    
    # 2. Device B logs in (should overwrite Device A)
    redis_client.store_token(user_id, token_device_B)
    print(f"\nDevice B logged in with token: {token_device_B}")
    
    # Verify Device B is valid
    is_valid_B = redis_client.validate_token(user_id, token_device_B)
    print(f"Device B token valid? {is_valid_B} (Expected: True)")
    
    # Verify Device A is now invalid
    is_valid_A_now = redis_client.validate_token(user_id, token_device_A)
    print(f"Device A token valid now? {is_valid_A_now} (Expected: False)")
    
    # 3. Device B logs out
    redis_client.revoke_token(user_id, token_device_B)
    print("\nDevice B logged out.")
    
    # Verify Device B is invalid
    is_valid_B_now = redis_client.validate_token(user_id, token_device_B)
    print(f"Device B token valid now? {is_valid_B_now} (Expected: False)")

if __name__ == "__main__":
    try:
        test_single_device_login()
    except Exception as e:
        print(f"Test failed with error: {e}")
