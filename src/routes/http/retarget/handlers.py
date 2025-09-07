from fastapi import APIRouter, Request, Depends
from proxy_handler_map import proxy_handler_map
from utils.headers import get_target_from_host
import logging

router = APIRouter()

@router.api_route(
    "/retarget/{retarget_proxy_to}/{url:path}",
    methods=["GET", "POST", "PUT", "DELETE", "HEAD"],
)
async def handle_retarget_call(
        retarget_proxy_to: str,
        url: str,
        request: Request,
        target: str = Depends(get_target_from_host),
        # identity
):
    # if not await check_map_access(request):
    #    return Response(load_heartbeat())
    module = proxy_handler_map.get(
        target
    )
    return await module.proxy_call(request, url, retarget_proxy_to) 