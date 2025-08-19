import re
import asyncio
from typing import Any, Optional

import logging

from fastapi import Response, Request
from fastapi import HTTPException

from aiohttp import ClientSession, ClientResponse


# from pydantic import BaseModel


from seleniumbase import Driver


from curl_cffi import requests

from bs4 import BeautifulSoup

from cache import AsyncTTL

import cloudscraper


from src.tools.proxy import inject_heartbeat

from src.process_proxy.envato.login import login
from src.process_proxy.tools import get_proxy_origin


# from src.tools.file import dump_to_file
from src.core.configs import configs


scraper = cloudscraper.create_scraper()  #

agent_string = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\
 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

selenium_load = {
    # "screens",
}

page_endpoint = {
    "browse",
    "apps",
    "flows",
    "ios",
    "screens",
}

forbidden_endpoints = {
    "login",
    "signup",
    "post",
    "comment",
    "leaderboard",
    "chat",
    "subscribe",
    "messages",
    "account",
    "settings"
    }

api_forbidden = {
    ("POST", "post"),
    ("DELETE", "post"),
    ("POST", "subscribe"),
    ("DELETE", "subscribe"),
    ("GET", "comment"),
    ("POST", "comment"),
    ("DELETE", "comment"),
    ("GET", "messages"),
    ("POST", "messages"),
    ("DELETE", "messages"),
    ("UPDATE", "messages"),
    ("GET", "realtime"),
    ("GET", "activity"),
    ("GET", "chat"),
    ("GET", "reader_referrals"),
    ("POST", "reader_referrals"),
    ("UPDATE", "reader_referrals"),
}


async def load_page(
    cookies,
    full_url,
) -> tuple:
    driver = Driver(
        browser="chrome",
        headless=True,
        uc=True,
        agent=agent_string,
    )
    driver.get(full_url)
    for cookie in cookies:
        driver.add_cookie(cookie)
    driver.refresh()

    return (
        driver.page_source,
        "text/html",
    )


async def load_page_with_cloudscraper(
    cookies,
    full_url,
):
    response = await asyncio.to_thread(
        scraper.get, full_url, cookies={item["name"]: item["value"] for item in cookies}
    )
    return (
        response.text,
        "text/html",
    )


def is_request_allowed(url: str, method):
    splitted = url.split("/")
    if splitted[0].split('?')[0] in ['projects', 'collections', 'account', 'subscription', 'claim-clear', 'pricing', 'sign-out']:
        return False
    return True
    if (
        splitted[0] == "api"
        and (str(method).upper(), splitted[2]) in api_forbidden
    ):
        return False
    if splitted[0]:
        return splitted[0] not in forbidden_endpoints
    return True


def is_selenium_full_load_needed(url: str):
    splitted = [part for part in url.split("/") if part]
    return splitted and splitted[0] in selenium_load


def is_slow_load_needed(
    url: str,
    method: str,
    accept: str,
):
    splitted = [part for part in url.split("/") if part]
    # splitted = url.split("/")
    return (
        (
            not splitted or splitted[0] in page_endpoint
        )  # Empty or first part in page_endpoints
        and method.upper() == "GET"  # Must be a GET request
        and "text/html" in accept.lower()  # Must accept text/html
    )


async def proxy_request(
    cookies,
    url_full,
    method,
    body,
    request
) -> Response:
    from starlette.responses import StreamingResponse
    import httpx
    import requests as base_requests
    proxy = await get_proxy_origin(5)
    logging.error(f"{proxy=}")
    headers = {k: v for k, v in request.headers.items()}
    headers['host'] = url_full.split('https://')[1].split('/')[0]
    headers['origin'] = "https://" + url_full.split('https://')[1].split('/')[0]
    if headers.get('referer'):
        del headers['referer']
    if headers.get('cookie'):
        del headers['cookie']

    proxies = {
                'http://': f'http://{proxy}',
                'https://': f'http://{proxy}'
                }
    resp_headers = {}
    #if "api/product/download" in url_full:
    #    async def stream_response():
    #        async with httpx.AsyncClient(proxy=proxies['http://']) as client:
    #            async with client.stream("GET", url_full, cookies=cookies) as response:
    #                resp_headers = response.headers
    #                async for chunk in response.aiter_bytes():
    #                    if chunk:
    #                        yield chunk
    #
    #    headers = {
    #                "Content-Disposition": 'attachment; filename="' + request.headers['Referer'].split('/')[-1] + '-collaboo.zip' + '"',
    #                "Content-Type": "application/zip"
    #            }
    #    return StreamingResponse(
    #            stream_response(),
    #            headers=headers
    #            )
    if "datadog-rum.js" in url_full:
        url_full = "https://www.datadoghq-browser-agent.com/us1/v5/datadog-rum.js"
    logging.error(request.cookies)

    langs = {
            "ru": "ru",
            "pt-br": "pt-BR",
            "fr": "fr",
            "es": "es",
            "de": "de"
            }
    select_lang = langs.get(url_full.replace('https://', '').split('/')[0], "en")



    cookies['preferredLanguage'] = select_lang




    async with requests.AsyncSession() as s:
        response = await s.request(
            method,
            url_full,
            data=body,
            cookies=cookies,
            proxies=proxies,
            headers=headers
        )


    logging.error(f'{url_full=}')
    #if response.status_code != 403:
    if True:
        if "html" in response.headers.get('content-type', ''):
            response.content = response.text.replace('elements.envato.com', 'elements.collaboo.co')
            response.content = response.content.replace('assets.elements.collaboo.co', 'elements.collaboo.co/assetssssssss_elementsss')
            response.content = response.content.replace('www.datadoghq-browser-agent.com/us1/v5/datadog-rum.js', 'elements.collaboo.co/datadog-rum.js')
            response.content = response.content.replace('account.envato.com', 'elements.collaboo.co')
            response.content = response.content.replace('labs.envato.com', 'labs-elements.collaboo.co')
            response.content = response.content.replace('assets.aws.labs-elements.collaboo.co', 'labs-elements.collaboo.co/assets_aws')
            response.content = response.content.replace('image-gen.aws.labs-elements.collaboo.co', 'labs-elements.collaboo.co/image_gen_aws')
            response.content = response.content.replace('api-gateway-websocket.aws.labs-elements.collaboo.co', 'labs-elements.collaboo.co/api_gateway_websocket')
            soup = BeautifulSoup(response.content, 'html.parser')


            style_tag = soup.new_tag("style")

            style_tag.string = 'button[data-testid="account-avatar"] {display: none;}'
            soup.head.append(style_tag)
            style_tag = soup.new_tag("style")

            style_tag.string = 'button[data-testid="account-parent-nav-item"] {display: none;}'
            soup.head.append(style_tag)
            style_tag = soup.new_tag("style")

            style_tag.string = 'div.ds-b1394h1w4.ds-b1394h6p.ds-b1394h1ru.ds-b1394h1os.ds-b1394h1io.ds-b1394h1lq.ds-b1394h3iy.ds-b1394h9r.ds-b1394hl.ds-b1394hh3.ds-b1394h3rt {display: none;}'
            soup.head.append(style_tag)
            response.content = str(soup)
        else:

            try:

                if "envato" not in response.text:
                    raise Exception()
                response.content = response.text.replace('elements.envato.com', 'elements.collaboo.co')
                response.content = response.content.replace('assets.elements.collaboo.co', 'elements.collaboo.co/assetssssssss_elementsss')
                response.content = response.content.replace('www.datadoghq-browser-agent.com/us1/v5/datadog-rum.js', 'elements.collaboo.co/datadog-rum.js')
                response.content = response.content.replace('account.envato.com', 'elements.collaboo.co')
                response.content = response.content.replace('labs.envato.com', 'labs-elements.collaboo.co')
                response.content = response.content.replace('api-gateway-assets.aws.labs-elements.collaboo.co', 'labs-elements.collaboo.co/assets_gateway_aws')
                response.content = response.content.replace('assets.aws.labs-elements.collaboo.co', 'labs-elements.collaboo.co/assets_aws')
                response.content = response.content.replace('image-gen.aws.labs-elements.collaboo.co', 'labs-elements.collaboo.co/image_gen_aws')
                response.content = response.content.replace('api-gateway-websocket.aws.labs-elements.collaboo.co', 'labs-elements.collaboo.co/api_gateway_websocket')
              #  response.content = response.content.replace('o.A.cookieDomain', '"elements.collaboo.co"')

                response.content = response.content.replace('api-gateway-labs-elements.collaboo.co', 'labs-elements.collaboo.co')
            except:
                ...
    try:
        if "/refresh_id_token" in response.text:
            response.content = response.text.replace('account.envato.com', 'elements.collaboo.co')
            response.content = response.content.replace('/refresh_id_token', '/accounts_data/refresh_id_token')
    except:
        ...
   # try:
   #     if "/api/product/download" in response.text:
   #         response.content = response.text.replace('/api/product/download', 'https://craftwork.design/api/product/download')
   # except:
   #     ...
    if "public/refresh_id_token" in url_full:
        cookies = dict(response.cookies)
        logging.error(response.content)
        import json
        logging.error(f"{cookies=}")
        with open("keys/envato_cookies.json") as f:
            f.write(json.dumps())
    return response


retarget_targets = {
    # "substack.com": f"{configs.CURRENT_HOST}",
    "uxmovement.substack.com": f"{configs.CURRENT_HOST}",
    "substackcdn.com": f"{configs.CURRENT_HOST}",
    "substack.com": f"nourl",
    f"{configs.CURRENT_HOST}/bundle": f"{configs.CURRENT_HOST}/retarget/substackcdn.com%2Fbundle",
    f"{configs.CURRENT_HOST}/image": f"{configs.CURRENT_HOST}/retarget/substackcdn.com%2Fimage",
    f"{configs.CURRENT_HOST}/static": f"{configs.CURRENT_HOST}/retarget/substackcdn.com%2Fstatic",
}


def replace_sensetive(html):
    for sensetive_data in configs.MOBBIN_REPLACE_SENSETIVE_DATA:
        html = re.sub(r"\b" + re.escape(sensetive_data) + r"\b", 'hidden', html)
    return html


def drop_to_http(html):
    if isinstance(html, bytes):
        return html

    html = re.sub(r"\b" + re.escape("https") + r"\b", "http", html)
    return html


def retarget(html):
    if isinstance(html, bytes):
        return html
    for target, replacement in retarget_targets.items():
        html = re.sub(r"\b" + re.escape(target) + r"\b", replacement, html)
    return html


morph_media_type = {
    "application/javascript",
    "application/javascript; charset=utf-8",
    "text/html" "text/html; charset=utf-8",
    "text/html; charset=utf-8",
    "application/json",
    "application/json; charset=utf-8",
    "text/plain; charset=UTF-8",
    "application/javascript; charset=UTF-8",
}

soup_media_type = {
    "text/html; charset=utf-8",
    "text/plain; charset=UTF-8",
    "text/html" "text/html; charset=utf-8",
}
block_media_type = {
    "application/javascript",
    "application/javascript; charset=utf-8",
}


def remove_profile_section(html, soup=None):
    if not soup:
        soup = BeautifulSoup(html, "html.parser")
    for tree_depth, element in configs.UXMOVEMENT_REMOVE_TAGS:
        elem = soup.find(**element)
        if elem:
            for i in range(0, tree_depth):
                elem = elem.find_parent()
            elem.decompose()
    return str(soup), soup


def morph_short_stuff(html, media_type):
    if str(media_type) not in morph_media_type:
        return html

    to_bytes_flag = False
    if isinstance(html, bytes):
        to_bytes_flag = True
        html = html.decode("utf-8")

    #if configs.DROP_TO_HTTTP:
    #    html = drop_to_http(html)

    if configs.RETARGET:
        html = retarget(html)
        html = replace_sensetive(html)

    if to_bytes_flag:
        return html.encode("utf-8")
    return html


@AsyncTTL(time_to_live=10000)
async def call(
    url,
    method,
    headers_accept,
    body,
    request
) -> Response:
    cookies = await asyncio.to_thread(login)
    resp = await proxy_request(cookies, url, method, body, request)
    return resp


async def proxy_call(
    request: Request,
    url: str,
    retarget: Optional[str] = None,
) -> Response:
    if not is_request_allowed(url, request.method):
        raise HTTPException(403)
    if str(request.query_params):
        url = url + "?" + str(request.query_params)
    url_full = "https://" + configs.TARGET_HOST + "/" + url
    if "assetssssssss_elementsss" in url_full:
        url_full = url_full.replace('assetssssssss_elementsss/', '')
        url_full = url_full.replace('elements.envato', 'assets.elements.envato')
    if "accounts_data" in url_full:
        url_full = url_full.replace('accounts_data/', '')
        url_full = url_full.replace('elements.envato', 'account.envato')
    if "assets_aws" in url_full:
        url_full = url_full.replace('assets_aws/', '')
        url_full = url_full.replace('labs.envato', 'assets.aws.labs.envato')
    if "image_gen_aws" in url_full:
        url_full = url_full.replace('image_gen_aws/', '')
        url_full = url_full.replace('labs.envato', 'image-gen.aws.labs.envato')
    if "api-gateway-websocket" in url_full:
        url_full = url_full.replace('image_gen_aws/', '')
        url_full = url_full.replace('labs.envato', 'api-gateway-websocket.aws.labs-elements.collaboo.co')
    if "assets_gateway_aws" in url_full:
        url_full = url_full.replace('assets_gateway_aws/', '')
        url_full = url_full.replace('labs.envato', 'api-gateway-assets.aws.labs.envato')
    logging.error(f"{url_full=}")
    return await call(
        url_full,
        request.method,
        request.headers.get("accept"),
        await request.body() if request.method not in {"GET", "HEAD"} else None,
        request
        )
