from fastapi import APIRouter, Request, Depends, HTTPException, Cookie, Response
import logging
from typing import Annotated
from core.configs import configs
from services.auth import check_credentials
from redis.asyncio import Redis
from infrastructure.redis import get_redis_client
from starlette.responses import RedirectResponse
from utils.headers import get_target, get_target_from_host
from proxy_handler_map import proxy_handler_map

logger = logging.getLogger(__name__)

router = APIRouter()

@router.api_route(
    "/{slug:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"]
)
async def handle_proxy_call(
        slug: str,
        request: Request,
        # identity: Annotated[Identity, Depends(identify_request)],
        authToken: Annotated[str, Cookie()],
        target: str = Depends(get_target_from_host),
        redis: Redis = Depends(get_redis_client),
):
    if target not in configs.TARGETS:
        raise HTTPException(status_code=404, detail="Target not found")
    
    # if check_map_access(request):
    cookies = {'authToken': authToken}
    if configs.AUTH_TYPE == "basic":
        if not check_credentials(redis, cookies, request, slug, target):
            return RedirectResponse("https://app.collaboo.co/login")
    
    url_full = slug
    if str(request.query_params):
        url_full = slug + "?" + str(request.query_params)
    try:
        if target == "refero" and request.method.upper() == "GET":
            cache_data = await redis.get(f"{url_full}__refero.design__data")
            cache_media_type = await redis.get(f"{url_full}__refero.design__media_type")
            if cache_data and cache_media_type:
                return Response(cache_data, media_type=cache_media_type.decode('utf-8'))
    except Exception as e:
        logging.error(f"Error!!! {e}, {e.args}")
    
    module = proxy_handler_map.get(target)
    if not module:
        raise HTTPException(status_code=404, detail="Handler not found for target")

    data = await module.proxy_call(request, slug)
    if target == "refero" and request.method.upper() == "GET":
        await redis.set(
        f"{url_full}__refero.design__data",
        data.content,
        60 * 60 * 24
    )
        await redis.set(
        f"{url_full}__refero.design__media_type",
        data.headers.get("content-type"),
        60 * 60 * 24

    )
    if data.headers.get('content-encoding'):
        del data.headers['content-encoding']
    if data.headers.get('Content-Length'):
        del data.headers['Content-Length']
    try:
        return Response(
    content=data.content,
    status_code=data.status_code,
    headers=data.headers,
    media_type=data.headers.get("content-type")
)
    except:
        return data