import redis.asyncio as redis
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

async def get_redis():
    client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    try:
        yield client
    finally:
        await client.close()
