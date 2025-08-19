import json
import logging
from typing import Annotated

from fastapi import FastAPI, Request, Response, Depends, HTTPException, Cookie, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

from curl_cffi import requests as async_requests
import requests

from src.core.configs import configs, tags_metadata

from src.tools.auth_deps import (
    identify_request,
    set_map_access,
    RequiresLogin,
    Identity
)

from src.process_proxy.mobbin import handlers as mobbin_handlers
from src.process_proxy.refero import handlers as refero_handlers
from src.process_proxy.uxmovement import handlers as uxmovement_handlers
from src.process_proxy.iconly import handlers as iconly_handlers
from src.process_proxy.craftwork import handlers as craftwork_handlers
from src.process_proxy.flaticon import handlers as flaticon_handlers
from src.process_proxy.freepik import handlers as freepik_handlers
from src.process_proxy.envato import handlers as envato_handlers


app = FastAPI(
    title=configs.PROJECT_NAME,
    version="0.0.1",
    docs_url=configs.DOCS_URL,
    openapi_tags=tags_metadata,
    openapi_url=f"{configs.API_V1_STR}/openapi.json",
)

if configs.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=configs.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

redis_app = Redis(
    host="redis",
    port=6379,
)

proxy_handler_map = {
    configs.MOBBIN_PROXY: mobbin_handlers,
    configs.UXMOVEMENT_PROXY: uxmovement_handlers,
    configs.REFERO_PROXY: refero_handlers,
    configs.ICONLY_PROXY: iconly_handlers,
    configs.CRAFTWORK_PROXY: craftwork_handlers,
    configs.FLATICON_PROXY: flaticon_handlers,
    configs.FREEPIK_PROXY: freepik_handlers,
    configs.ENVATO_PROXY: envato_handlers,
    configs.ENVATO_LABS_PROXY: envato_handlers,
    }


@app.exception_handler(RequiresLogin)
async def requires_login(request: Request, _: Exception):
    return RedirectResponse("https://app.collaboo.co/login")


@app.get("/proxy-login")
async def login(
        token: str,
        request: Request,
):
    return HTMLResponse(
        login_html(token)
    )


@app.post("/proxy-heartbeat")
async def heartbeat(
        request: Request,
        identity: Annotated[Identity, Depends(identify_request)],
):
    proxy_relation = await subs_req.get_user_proxy_relation(
        identity.profile.user_id,
        configs.PROXY_TARGET,
    )
    logging.warning(proxy_relation)
    logging.warning(identity.profile.user_id)
    if not await identity.check_proxy_access(
            proxy_relation,
    ):
        raise HTTPException(401)
    await set_map_access(request)
    return 'ok'


@app.api_route(
    "/retarget/{retarget_proxy_to}/{url:path}",
    methods=["GET", "POST", "PUT", "DELETE", "HEAD"],
)
async def handle_retarget_call(
        retarget_proxy_to: str,
        url: str,
        request: Request,
        # identity
):
    logging.warning(retarget_proxy_to)
    # if not await check_map_access(request):
    #    return Response(load_heartbeat())
    module = proxy_handler_map.get(
        configs.PROXY_TARGET,
    )
    return await module.proxy_call(request, url, retarget_proxy_to)

active_connections = []
messages = {}

def on_close(ws):
    print("Соединение закрыто")

@app.websocket("/{url:path}")
async def websocket_endpoint(url: str, websocket: WebSocket):
    import websocket as websocket_import
    import uuid
    import threading
    import asyncio
    await websocket.accept()
    query_params = websocket.query_params
    ws_uuid = str(uuid.uuid4())
    def on_open(ws):
        import threading
        import time
        def run(*args):
            while True:
                time.sleep(1)
                logging.error(f"{messages=}")
                msg_ids = []
                for ids, msg in messages.items():
                    if "//" + ws_uuid not in ids:
                        continue
                    msg = msg.replace('labs-elements.collaboo.co/assets_aws',
                                      'api-gateway-assets.aws.labs.envato.com')
                    ws.send(msg)
                    msg_ids.append(ids)
                for ids in msg_ids:
                    try:
                        del messages[ids]
                    except:
                        ...

        thread = threading.Thread(target=run)
        thread.start()
    def on_message(ws, message):
        asyncio.run(websocket.send_text(message))
    def run_websocket():
        url_send = "wss://api-gateway-websocket.aws.labs.envato.com/"
        if query_params.get('token'):
            url_send += "?token=" + query_params.get('token')
        wsocket = websocket_import.WebSocketApp(url_send,
                                on_message=on_message,
                                on_close=on_close,
                                header={
  #      "Upgrade": "websocket",
        "Origin": "https://labs.envato.com",
        "Cache-Control": "no-cache",
        "Accept-Language": "ru,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
        "Pragma": "no-cache",
  #      "Connection": "Upgrade",
     #   "Sec-WebSocket-Key": "HBkcVaoEOJlKXDsQReuy0A==",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0",
        "Sec-WebSocket-Version": "13",
  #      "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits"
    }
                                     )
        wsocket.on_open = on_open
        wsocket.run_forever(
                http_proxy_host="109.197.20.16",
                http_proxy_port=62952,
                http_proxy_auth=("hYqtKMwk", "LwrCg3JN"),
                proxy_type="http"
            )
    active_connections.append(websocket)
    thread = threading.Thread(target=run_websocket)
    thread.start()
    try:
        while True:
            data = await websocket.receive_text()
            messages[str(uuid.uuid4()) + "//" + ws_uuid] = data
            logging.error(f"{data=}")
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        await websocket.close()





async def check_credentials(cookies, request, url) -> bool:
    if request.method != "GET":
        return True
    if "." in url:
        return True

    if await redis_app.get(f"{cookies['authToken']}__{configs.TARGET_HOST}"):
        return True

    res = requests.get('http://82.202.131.128:8001/api-subs/api/v1/sub-layout/get_active_sub', cookies=cookies)
    site = "uxmov"
    if configs.TARGET_HOST == "mobbin.com":
        site = "mobbin"
    if configs.TARGET_HOST == "refero.design":
        site = "refero"
    if configs.TARGET_HOST == "iconly.pro":
        site = "iconly"
    if configs.TARGET_HOST == "craftwork.design":
        site = "craftwork"
    if configs.TARGET_HOST == "www.flaticon.com":
        site = "flaticon"
    if configs.TARGET_HOST == "www.freepik.com":
        site = "freepik"
    if configs.TARGET_HOST in ["labs.envato.com", "elements.envato.com"]:
        site = "elements"
    for el in res.json():
        if site in el['links'][0]['href']:
            await redis_app.set(f"{cookies['authToken']}__{configs.TARGET_HOST}", "True", 60 * 60)
            return True
    logging.error(site)
    return False

class Url(BaseModel):
    url: str


@app.post("/get_screens_from_url")
async def get_screens_from_url(
        url: Url,
        request: Request,
        authToken: Annotated[str, Cookie()]
):
    url = url.url
    cookies = {'authToken': authToken}
    if await check_credentials(cookies, request, url):
        logging.warning(url)

        url = "-".join(url.split('apps/')[1].split('/')[0].split('-')[3:])
        logging.warning(url)
        #if await redis_app.get(url):
        #    return json.loads(await redis_app.get(url))
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
            await redis_app.set(url, json.dumps(urls), 60 * 60)
        except Exception as e:
            logging.error(e)
        return urls
    return []

@app.get(
    "/manifest.webmanifest"
)
async def handle_proxy_manifest_call(request: Request):
    module = proxy_handler_map.get(configs.PROXY_TARGET)
    logging.error(module)
    data = await module.proxy_call(request, "manifest.webmanifest")
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


@app.get(
    "/manifest.json"
)
async def handle_proxy_manifest_call(request: Request):
    module = proxy_handler_map.get(configs.PROXY_TARGET)
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

@app.api_route(
    "/{url:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"]
)
async def handle_proxy_call(
        url: str,
        request: Request,
        identity: Annotated[Identity, Depends(identify_request)],
        authToken: Annotated[str, Cookie()]
):
    # if check_map_access(request):
    cookies = {'authToken': authToken}

    if await check_credentials(cookies, request, url):
        url_full = url
        if str(request.query_params):
            url_full = url + "?" + str(request.query_params)
        try:
            # logging.error('test')
            # logging.error(configs.PROXY_TARGET == "refero.design")
            if configs.TARGET_HOST == "refero.design" and request.method.upper() == "GET":
                cache_data = await redis_app.get(f"{url_full}__{configs.TARGET_HOST}__data")
                cache_media_type = await redis_app.get(f"{url_full}__{configs.TARGET_HOST}__media_type")
                if cache_data and cache_media_type:
                    return Response(cache_data, media_type=cache_media_type.decode('utf-8'))
        except Exception as e:
            logging.error(f"Error!!! {e}, {e.args}")
        module = proxy_handler_map.get(configs.PROXY_TARGET)
        data = await module.proxy_call(request, url)
        if configs.TARGET_HOST == "refero.design" and request.method.upper() == "GET":
            await redis_app.set(
            f"{url_full}__{configs.TARGET_HOST}__data",
            data.content,
            60 * 60 * 24
        )
            await redis_app.set(
            f"{url_full}__{configs.TARGET_HOST}__media_type",
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
    return RedirectResponse("https://app.collaboo.co/login")


def load_heartbeat():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <script>
        // Send initial heartbeat immediately

        function sendHeartbeat() {
            const res = fetch('/proxy-heartbeat', {
                method: 'POST',
                credentials: 'include' // This ensures cookies are sent
            });
            if (res.status == 401) {
                const refreshed = await refreshTokens();
                if (refreshed) {
                    return await sendHeartbeat(); // retry after refresh
                } else {
                    throw new Error("Token refresh failed");
                }
            }
        }

        async function refreshTokens() {
            const refreshToken = getCookie("refresh_token");
            const res = await fetch("https://securetoken.googleapis.com/v1/token?key=AIzaSyAxfFm_vWEz4_h3xOD9DApqRTdTjbq2crY", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                body: new URLSearchParams({
                    grant_type: "refresh_token",
                    refresh_token: refreshToken
                })
            });
            if (!res.ok) return false;
            const data = await res.json();
            document.cookie = `proxy_jwt=Bearer ${data.id_token}; path=/; domain=.yourdomain.com; secure; SameSite=None`;
            document.cookie = `refresh_token=${data.refresh_token}; path=/; domain=.yourdomain.com; secure; SameSite=None`;
        }

        sendHeartbeat();
        // Continue sending every 15s
        setInterval(() => sendHeartbeat, 15000);

        // Reload after 20s
        setTimeout(() => {
          location.reload();
        }, 1000);
      </script>
    </head>
    <body>
      <h2>Setting up your session...</h2>
      <p>This page will reload shortly to load the target content.</p>
    </body>
    </html>
    """


def load_hearbeat_with_firebase():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
    </head>
    <body>
      <script type="module">
        import { initializeApp } from "https://www.gstatic.com/firebasejs/10.0.0/firebase-app.js";
        import { getAuth, onAuthStateChanged, getIdToken } from "https://www.gstatic.com/firebasejs/10.0.0/firebase-auth.js";

        const firebaseConfig = {
          apiKey: "AIzaSyAxfFm_vWEz4_h3xOD9DApqRTdTjbq2crY",
          authDomain: "local-soulwi.firebaseapp.com",
          projectId: "local-soulwi",
          storageBucket: "local-soulwi.appspot.com",
          messagingSenderId: "944388395479",
          appId: "1:944388395479:web:b160914f7f0a09a2083b92"
        };

        const app = initializeApp(firebaseConfig);
        const auth = getAuth(app);

        async function sendHeartbeat() {
            const res = await fetch('/proxy-heartbeat', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${auth.currentUser.accessToken}`
                }
            });
        }

        onAuthStateChanged(auth, async function (user) {
            await sendHeartbeat();
            setTimeout(() => {
              location.reload();
            }, 1000);
        });

      </script>
      <h2>Setting up your session...</h2>
      <p>This page will reload shortly to load the target content.</p>
    </body>
    </html>
    """


def login_html(token):
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
    </head>
    <body>
      <script type="module">
        import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/10.0.0/firebase-app.js";
        import {{ getAuth, onAuthStateChanged, getIdToken, signInWithCustomToken }} from "https://www.gstatic.com/firebasejs/10.0.0/firebase-auth.js";

        const firebaseConfig = {{
          apiKey: "AIzaSyAxfFm_vWEz4_h3xOD9DApqRTdTjbq2crY",
          authDomain: "local-soulwi.firebaseapp.com",
          projectId: "local-soulwi",
          storageBucket: "local-soulwi.appspot.com",
          messagingSenderId: "944388395479",
          appId: "1:944388395479:web:b160914f7f0a09a2083b92"
        }};

        const app = initializeApp(firebaseConfig);
        const auth = getAuth(app);

        signInWithCustomToken(auth, "{token}")
          .then((userCredential) => {{
            const user = userCredential.user;
          }})
          .catch((error) => {{
              console.log(error)
          }});

        setTimeout(() => {{
            document.location.href = "/"
        }}, 4000);
      </script>
      <h2>Setting up your session...</h2>
      <p>This page will reload shortly to load the target content.</p>
    </body>
    </html>
    """
