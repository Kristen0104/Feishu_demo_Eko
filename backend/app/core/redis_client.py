"""
Redis 客户端模块
管理 Redis 连接，提供缓存和 Pub/Sub 功能用于实时消息推送
"""
import redis.asyncio as redis
from app.config import settings

redis_client: redis.Redis | None = None


async def init_redis():
    global redis_client
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
    )
    await redis_client.ping()
    return redis_client


async def get_redis() -> redis.Redis:
    return redis_client


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


async def publish(channel: str, message: str):
    if redis_client:
        await redis_client.publish(channel, message)


async def get_cache(key: str) -> str | None:
    if redis_client:
        return await redis_client.get(key)
    return None


async def set_cache(key: str, value: str, expire: int = 300):
    if redis_client:
        await redis_client.set(key, value, ex=expire)


async def delete_cache(key: str):
    if redis_client:
        await redis_client.delete(key)
