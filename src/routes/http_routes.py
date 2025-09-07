import json
import logging
from typing import Annotated

from fastapi import Request, Response, Depends, HTTPException, Cookie, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from starlette.responses import RedirectResponse, HTMLResponse

from curl_cffi import requests as async_requests
import requests

from app_instance import app, proxy_handler_map, redis_app
from core.configs import configs
from tools.auth_deps import (
    identify_request,
    set_map_access,
    RequiresLogin,
    Identity,
)
from tools.headers import get_target, get_target_from_host
from utils.templates import login_html
from requests import subs as subs_req


@app.exception_handler(RequiresLogin)
async def requires_login(request: Request, _: Exception):
    return RedirectResponse("https://app.collaboo.co/login")








@app.api_route(
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
    logging.info(f"")
    # if not await check_map_access(request):
    #    return Response(load_heartbeat())
    module = proxy_handler_map.get(
        target
    )
    return await module.proxy_call(request, url, retarget_proxy_to)


active_connections = []
messages = {}





async def check_credentials(cookies, request, url, target: str) -> bool:
    if request.method != "GET":
        return True
    if "." in url:
        return True

    if await redis_app.get(f"{cookies['authToken']}__{target}"):
        return True

    res = requests.get('http://82.202.131.128:8001/api-subs/api/v1/sub-layout/get_active_sub', cookies=cookies)

    for el in res.json():
        if site in el['links'][0]['href']:
            await redis_app.set(f"{cookies['authToken']}__{target}", "True", 60 * 60)
            return True
    logging.error(site)
    return False


class Url(BaseModel):
    url: str














