from redis.asyncio import Redis
import requests
import logging


async def check_credentials(redis: Redis, cookies, request, url, target: str) -> bool:
    if request.method != "GET":
        return True
    if "." in url:
        return True

    if await redis.get(f"{cookies['authToken']}__{target}"):
        return True

    res = requests.get('http://82.202.131.128:8001/api-subs/api/v1/sub-layout/get_active_sub', cookies=cookies)
    
    for el in res.json():
        if site in el['links'][0]['href']:
            await redis.set(f"{cookies['authToken']}__{target}", "True", 60 * 60)
            return True
    logging.error(site)
    return False