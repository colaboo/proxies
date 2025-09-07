from redis.asyncio import Redis
from core.configs import configs

redis_client: Redis = None

async def init_redis():
    global redis_client
    redis_client = Redis(
    host=configs.REDIS_HOST,
    port=configs.REDIS_PORT,
    db=configs.REDIS_DB,
)

async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()

async def get_redis_client():
    return redis_client