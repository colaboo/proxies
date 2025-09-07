# import json
# import logging
# from typing import Annotated

# from fastapi import FastAPI, Request, Response, Depends, HTTPException, Cookie, WebSocket, WebSocketDisconnect
# from redis.asyncio import Redis
# from pydantic import BaseModel
# from starlette.middleware.cors import CORSMiddleware
# from starlette.responses import RedirectResponse

# from curl_cffi import requests as async_requests
# import requests

# from core.configs import configs, tags_metadata

# from tools.auth_deps import (
#     identify_request,
#     set_map_access,
#     RequiresLogin,
#     Identity
# )

# from process_proxy.mobbin import handlers as mobbin_handlers
# from process_proxy.refero import handlers as refero_handlers
# from process_proxy.uxmovement import handlers as uxmovement_handlers
# from process_proxy.iconly import handlers as iconly_handlers
# from process_proxy.craftwork import handlers as craftwork_handlers
# from process_proxy.flaticon import handlers as flaticon_handlers
# from process_proxy.freepik import handlers as freepik_handlers
# from process_proxy.envato import handlers as envato_handlers
# from tools.headers import get_target, get_target_from_host
# from core.logging_setup import setup_logging

# setup_logging()

# def load_heartbeat():
#      with open("templates/heartbeat.html", "r", encoding="utf-8") as f:
#         return f.read()


# def load_heartbeat_with_firebase():
#      with open("templates/firebase_heartbeat.html", "r", encoding="utf-8") as f:
#         return f.read()



# def login_html(token):
#      with open("templates/login.html", "r", encoding="utf-8") as f:
#         return f.read().format(token=token)
# app = FastAPI(
#     title=configs.PROJECT_NAME,
#     version="0.0.1",
#     docs_url=configs.DOCS_URL,
#     openapi_tags=tags_metadata,
#     openapi_url=f"{configs.API_V1_STR}/openapi.json",
# )

# if configs.BACKEND_CORS_ORIGINS:
#     app.add_middleware(
#         CORSMiddleware,
#         allow_origins=configs.BACKEND_CORS_ORIGINS,
#         allow_credentials=True,
#         allow_methods=["*"],
#         allow_headers=["*"],
#     )



# proxy_handler_map = {
#     "mobbin": mobbin_handlers,
#     "uxmovement": uxmovement_handlers,
#     "refero": refero_handlers,
#     "iconly": iconly_handlers,
#     "craftwork": craftwork_handlers,
#     "flaticon": flaticon_handlers,
#     "freepik": freepik_handlers,
#     "envato": envato_handlers,
# }
# @app.get("/health")
# async def health():
#     return {"status": "ok"}

# @app.exception_handler(RequiresLogin)
# async def requires_login(request: Request, _: Exception):
#     return RedirectResponse("https://app.collaboo.co/login")


# @app.get("/proxy-login")
# async def login(
#         token: str,
#         request: Request,
# ):
#     return HTMLResponse(
#         login_html(token)
#     )


# @app.post("/proxy-heartbeat")
# async def heartbeat(
#         request: Request,
#         identity: Annotated[Identity, Depends(identify_request)],
# ):
#     proxy_relation = await subs_req.get_user_proxy_relation(
#         identity.profile.user_id,
#         configs.PROXY_TARGET,
#     )
#     logging.warning(proxy_relation)
#     logging.warning(identity.profile.user_id)
#     if not await identity.check_proxy_access(
#             proxy_relation,
#     ):
#         raise HTTPException(401)
#     await set_map_access(request)
#     return 'ok'


# @app.api_route(
#     "/retarget/{retarget_proxy_to}/{url:path}",
#     methods=["GET", "POST", "PUT", "DELETE", "HEAD"],
# )
# async def handle_retarget_call(
#         retarget_proxy_to: str,
#         url: str,
#         request: Request,
#         target: str = Depends(get_target_from_host),
#         # identity
# ):
#     logging.info(f"")
#     # if not await check_map_access(request):
#     #    return Response(load_heartbeat())
#     module = proxy_handler_map.get(
#         target
#     )
#     return await module.proxy_call(request, url, retarget_proxy_to)

# active_connections = []
# messages = {}

# def on_close(ws):
#     print("Соединение закрыто")

# @app.websocket("/{url:path}")
# async def websocket_endpoint(url: str, websocket: WebSocket):
#     import websocket as websocket_import
#     import uuid
#     import threading
#     import asyncio
#     await websocket.accept()
#     query_params = websocket.query_params
#     ws_uuid = str(uuid.uuid4())
#     def on_open(ws):
#         import threading
#         import time
#         def run(*args):
#             while True:
#                 time.sleep(1)
#                 logging.error(f"{messages=}")
#                 msg_ids = []
#                 for ids, msg in messages.items():
#                     if "//" + ws_uuid not in ids:
#                         continue
#                     msg = msg.replace('labs-elements.collaboo.co/assets_aws',
#                                       'api-gateway-assets.aws.labs.envato.com')
#                     ws.send(msg)
#                     msg_ids.append(ids)
#                 for ids in msg_ids:
#                     try:
#                         del messages[ids]
#                     except:
#                         ...

#         thread = threading.Thread(target=run)
#         thread.start()
#     def on_message(ws, message):
#         asyncio.run(websocket.send_text(message))
#     def run_websocket():
#         url_send = "wss://api-gateway-websocket.aws.labs.envato.com/"
#         if query_params.get('token'):
#             url_send += "?token=" + query_params.get('token')
#         wsocket = websocket_import.WebSocketApp(url_send,
#                                 on_message=on_message,
#                                 on_close=on_close,
#                                 header={
#   #      "Upgrade": "websocket",
#         "Origin": "https://labs.envato.com",
#         "Cache-Control": "no-cache",
#         "Accept-Language": "ru,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
#         "Pragma": "no-cache",
#   #      "Connection": "Upgrade",
#      #   "Sec-WebSocket-Key": "HBkcVaoEOJlKXDsQReuy0A==",
#         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0",
#         "Sec-WebSocket-Version": "13",
#   #      "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits"
#     }
#                                      )
#         wsocket.on_open = on_open
#         wsocket.run_forever(
#                 http_proxy_host="109.197.20.16",
#                 http_proxy_port=62952,
#                 http_proxy_auth=("hYqtKMwk", "LwrCg3JN"),
#                 proxy_type="http"
#             )
#     active_connections.append(websocket)
#     thread = threading.Thread(target=run_websocket)
#     thread.start()
#     try:
#         while True:
#             data = await websocket.receive_text()
#             messages[str(uuid.uuid4()) + "//" + ws_uuid] = data
#             logging.error(f"{data=}")
#     except WebSocketDisconnect:
#         active_connections.remove(websocket)
#         await websocket.close()





# async def check_credentials(cookies, request, url, target: str) -> bool:
#     if request.method != "GET":
#         return True
#     if "." in url:
#         return True

#     if await redis_app.get(f"{cookies['authToken']}__{target}"):
#         return True

#     res = requests.get('http://82.202.131.128:8001/api-subs/api/v1/sub-layout/get_active_sub', cookies=cookies)
    
#     for el in res.json():
#         if site in el['links'][0]['href']:
#             await redis_app.set(f"{cookies['authToken']}__{target}", "True", 60 * 60)
#             return True
#     logging.error(site)
#     return False

# class Url(BaseModel):
#     url: str


# @app.post("/get_screens_from_url")
# async def get_screens_from_url(
#         url: Url,
#         request: Request,
#         authToken: Annotated[str, Cookie()],
#         target: str = Depends(get_target),
# ):
#     url = url.url
#     cookies = {'authToken': authToken}
#     if await check_credentials(cookies, request, url, target):
#         logging.warning(url)

#         url = "-".join(url.split('apps/')[1].split('/')[0].split('-')[3:])
#         logging.warning(url)
#         #if await redis_app.get(url):
#         #    return json.loads(await redis_app.get(url))
#         json_data = {
#             'appId': url,
#         }
#         logging.warning('123')
#         async with async_requests.AsyncSession() as s:
#             response = await s.post(
#             'https://dev-mobbin.collaboo.co/api/app/fetch-app-versions-screens',
#             cookies=cookies,
#             json=json_data,
#         )
#         logging.warning(response)
#         urls = []
#         try:
#             for version in response.json()['value']['appVersions']:
#                 for appScreens in version['appScreens']:
#                     urls.append({'id': appScreens['id'], 'link': appScreens['screenUrl']})
#             await redis_app.set(url, json.dumps(urls), 60 * 60)
#         except Exception as e:
#             logging.error(e)
#         return urls
#     return []

# @app.get(
#     "/manifest.webmanifest"
# )
# async def handle_proxy_manifest_call(request: Request, target: str = Depends(get_target)):
#     module = proxy_handler_map.get(target)
#     logging.error(module)
#     data = await module.proxy_call(request, "manifest.webmanifest")
#     if data.headers.get('content-encoding'):
#         del data.headers['content-encoding']
#     if data.headers.get('Content-Length'):
#         del data.headers['Content-Length']
#     try:
#         return Response(
#     content=data.content,
#     status_code=data.status_code,
#     headers=data.headers,
#     media_type=data.headers.get("content-type")
# )
#     except:
#         return data


# @app.get(
#     "/manifest.json"
# )
# async def handle_proxy_manifest_call(request: Request, target: str = Depends(get_target)):
#     module = proxy_handler_map.get(target)
#     logging.error(module)
#     data = await module.proxy_call(request, "manifest.json")
#     if data.headers.get('content-encoding'):
#         del data.headers['content-encoding']
#     if data.headers.get('Content-Length'):
#         del data.headers['Content-Length']
#     try:
#         return Response(
#     content=data.content,
#     status_code=data.status_code,
#     headers=data.headers,
#     media_type=data.headers.get("content-type")
# )
#     except:
#         return data

# @app.api_route(
#     "/{url:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"]
# )
# async def handle_proxy_call(
#         url: str,
#         request: Request,
#         identity: Annotated[Identity, Depends(identify_request)],
#         authToken: Annotated[str, Cookie()],
#         target: str = Depends(get_target_from_host),
# ):
#     logging.info(target)
#     # Проверяем, что target находится в списке разрешенных TARGETS
#     if target not in configs.TARGETS:
#         raise HTTPException(status_code=404, detail="Target not found")
    
#     # if check_map_access(request):
#     cookies = {'authToken': authToken}
#     if configs.AUTH_TYPE == "basic":
#         if not check_credentials(cookies, request, url, target):
#             return RedirectResponse("https://app.collaboo.co/login")
    
#     url_full = url
#     if str(request.query_params):
#         url_full = url + "?" + str(request.query_params)
#     try:
#         if target == "refero" and request.method.upper() == "GET":
#             cache_data = await redis_app.get(f"{url_full}__refero.design__data")
#             cache_media_type = await redis_app.get(f"{url_full}__refero.design__media_type")
#             if cache_data and cache_media_type:
#                 return Response(cache_data, media_type=cache_media_type.decode('utf-8'))
#     except Exception as e:
#         logging.error(f"Error!!! {e}, {e.args}")
    
#     module = proxy_handler_map.get(target)
#     if not module:
#         raise HTTPException(status_code=404, detail="Handler not found for target")

#     data = await module.proxy_call(request, url)
#     if target == "refero" and request.method.upper() == "GET":
#         await redis_app.set(
#         f"{url_full}__refero.design__data",
#         data.content,
#         60 * 60 * 24
#     )
#         await redis_app.set(
#         f"{url_full}__refero.design__media_type",
#         data.headers.get("content-type"),
#         60 * 60 * 24

#     )
#     if data.headers.get('content-encoding'):
#         del data.headers['content-encoding']
#     if data.headers.get('Content-Length'):
#         del data.headers['Content-Length']
#     try:
#         return Response(
#     content=data.content,
#     status_code=data.status_code,
#     headers=data.headers,
#     media_type=data.headers.get("content-type")
# )
#     except:
#         return data