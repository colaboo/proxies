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

from src.process_proxy.craftwork.login import login
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
    urls_forbidden = ['pro-access-area', 'subscriptions', 'downloads', 'orders', 'saved', 'settings', 'shopping-cart', 'become-an-author']
    for url_f in urls_forbidden:
        if splitted[0].replace('/', '').split('?')[0] == url_f:
            return False

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

    url_full = url_full.replace('/cchunksssss/', '/chunks/')
    proxies = {
                'http://': f'http://{proxy}',
                'https://': f'http://{proxy}'
                }
    resp_headers = {}
    if "api/product/download" in url_full:
        async def stream_response():
            async with httpx.AsyncClient(proxy=proxies['http://']) as client:
                async with client.stream("GET", url_full, cookies=cookies) as response:
                    resp_headers = response.headers
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            yield chunk

        headers = {
                    "Content-Disposition": 'attachment; filename="' + request.headers['Referer'].split('/')[-1] + '-collaboo.zip' + '"',
                    "Content-Type": "application/zip"
                }
        return StreamingResponse(
                stream_response(),
                headers=headers
                )

    async with requests.AsyncSession() as s:
        response = await s.request(
            method,
            url_full,
            data=body,
            cookies=cookies,
            proxies=proxies
        )

    if "html" in response.headers.get('content-type', ''):
        response.content = response.text.replace('craftwork.design', 'dev-craftwork.collaboo.co')
        response.content = response.text.replace('/chunks/', '/cchunksssss/')
        soup = BeautifulSoup(response.content, 'html.parser')

        style_tag = soup.new_tag("style")
        style_tag.string = 'nav[class="flex gap-[25px] items-center"] {display: none;}'
        soup.head.append(style_tag)
        script_tag = soup.new_tag('script')
        script_tag.string = """
                // Установка refero_token в localStorage при загрузке страницы

            setInterval(() => {
  document.querySelectorAll('a[aria-label="Открытый чат"]').forEach(link => link.remove());
  document.querySelectorAll('nav[class="flex gap-[25px] items-center"]').forEach(div => div.remove());
}, 10);
            """
        if soup.body:
            soup.body.append(script_tag)


        response.content = str(soup)

    try:
        if "pendingMpaPath!==" in response.text:
            response.content = response.text.replace('j.pendingMpaPath!==p', 'p!==window.location.href')

    except:
        ...
   # try:
   #     if "/api/product/download" in response.text:
   #         response.content = response.text.replace('/api/product/download', 'https://craftwork.design/api/product/download')
   # except:
   #     ...
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
    if retarget:
        url_full = "https://" + retarget + "/" + url
    return await call(
        url_full,
        request.method,
        request.headers.get("accept"),
        await request.body() if request.method not in {"GET", "HEAD"} else None,
        request
        )
