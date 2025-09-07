from redis.asyncio import Redis
from curl_cffi import requests
from core.configs import configs

redis_app = Redis(
    host=configs.REDIS_HOST,
    port=configs.REDIS_PORT,
    db=configs.REDIS_DB,
)


async def get_proxy_origin(proxy_id: int):
    proxy = await redis_app.get('iconly_proxy')
    if not proxy:
        async with requests.AsyncSession() as s:
            response = await s.request(
                "GET",
                "https://app.collaboo.co/api-support/api/v1/config/?iconly_proxy=4"
                    )
            data = response.json()
            proxy = data['proxy_site']
            await redis_app.set('iconly_proxy', proxy, 60 * 5)
    if isinstance(proxy, bytes):
        proxy = proxy.decode()
    return proxy
