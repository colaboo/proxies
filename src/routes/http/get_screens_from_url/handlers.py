from fastapi import APIRouter, Request, Depends, HTTPException, Cookie
import logging
from typing import Annotated
from utils import get_target_from_host
from core.configs import configs
from services.auth import check_credentials
from redis.asyncio import Redis
import json
from pydantic import BaseModel
from infrastructure.redis import get_redis_client

router = APIRouter()

class Url(BaseModel):
    url: str

@router.post("/get_screens_from_url")
async def get_screens_from_url(
        url: Url,
        request: Request,
        authToken: Annotated[str, Cookie()],
        target: str = Depends(get_target_from_host),
        redis: Redis = Depends(get_redis_client),
):
    url = url.url
    cookies = {'authToken': authToken}
    if await check_credentials(cookies, request, url, target):
        logging.warning(url)

        url = "-".join(url.split('apps/')[1].split('/')[0].split('-')[3:])
        logging.warning(url)
        #if await redis.get(url):
        #    return json.loads(await redis.get(url))
        json_data = {
            'appId': url,
        }
        logging.warning('123')
        async with async_requests.AsyncSession() as s:
            response = await s.post(
            'https://dev-mobbin.collaboo.co/api/app/fetch-app-versions-screens',
            cookies=cookies,
            json=json_data,
        )
        logging.warning(response)
        urls = []
        try:
            for version in response.json()['value']['appVersions']:
                for appScreens in version['appScreens']:
                    urls.append({'id': appScreens['id'], 'link': appScreens['screenUrl']})
            await redis.set(url, json.dumps(urls), 60 * 60)
        except Exception as e:
            logging.error(e)
        return urls
    return []