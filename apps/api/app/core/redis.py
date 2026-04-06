"""Redis 配置"""

import redis.asyncio as redis
from app.core.config import settings

# Redis 连接池
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True
)


async def get_redis():
    """获取 Redis 连接"""
    return redis.Redis(connection_pool=redis_pool)


async def test_redis():
    """测试 Redis 连接"""
    r = await get_redis()
    await r.set("test_key", "test_value")
    value = await r.get("test_key")
    print(f"✅ Redis 连接成功: {value}")
    return value
