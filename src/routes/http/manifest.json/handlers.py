from fastapi import APIRouter, Request, Depends, Response
import logging
from proxy_handler_map import proxy_handler_map
from utils.headers import get_target_from_host

router = APIRouter()

@router.get(
    "/manifest.json"
)
async def handle_proxy_manifest_call(request: Request, target: str = Depends(get_target_from_host)):
    module = proxy_handler_map.get(target)
    logging.error(module)
    data = await module.proxy_call(request, "manifest.json")
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