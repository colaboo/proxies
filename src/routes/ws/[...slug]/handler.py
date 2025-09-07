from fastapi import APIRouter, WebSocket
import logging


logger = logging.getLogger(__name__)

router = APIRouter()


def on_close(ws):
    print("Соединение закрыто")


@router.websocket("/{slug:path}")
async def websocket_endpoint(slug: str, websocket: WebSocket):
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