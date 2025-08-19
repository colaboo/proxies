import re
import asyncio
from typing import Any, Optional
import json
import logging

from fastapi import Response, Request
from fastapi import HTTPException

from aiohttp import ClientSession, ClientResponse

from starlette.responses import RedirectResponse

# from pydantic import BaseModel


from redis.asyncio import Redis
from seleniumbase import Driver


from curl_cffi import requests

from bs4 import BeautifulSoup

from cache import AsyncTTL

import cloudscraper


from src.tools.proxy import inject_heartbeat

from src.process_proxy.iconly.login import login

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
    "login"
    "signup",
    "settings",
    "saved",
    "pricing"
    }

api_forbidden = {
    ("GET", "recent-searches"),
    ("POST", "user"),
    ("GET", "churnkey"),
    ("GET", "saved"),
    ("POST", "saved"),
    ("GET", "collection"),
    ("POST", "collection"),
}


redis_app = Redis(
    host="redis",
    port=6379,
)




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
    logging.error(f"{url.split('?')[0]=}")
    if url.split('?')[0].split('/')[0] in ["/settings", "/settings/", "settings/", "settings"]:
        return False
    return True
    if splitted == "api" and splitted[1] != api_forbidden[method]:
        return False
    if "app-requests/new-app" in url:
        return False
    if "mail/support/send-support-mail" in url:
        return False
    if "/settings" in url:
        return False
    if "/pricing" in url:
        return False
    if "settings/" in url:
        return False
    if "pricing/" in url:
        return False
    if "settings" == url:
        return False
    if "pricing" == url:
        return False
    if method == "GET":
        return True
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
    request,
    not_headers = True
) -> Response:
    headers = {k: v for k, v in request.headers.items()}
    headers['host'] = "web.iconly.pro"
    is_web = False
    if headers.get('referer'):
        if "co/web" in headers.get('referer'):
            is_web = True
        del headers['referer']
    if headers.get('cookie'):
        del headers['cookie']
    logging.error(url_full)
    if not_headers:
        headers = {}
    if is_web:
        url_full = url_full.replace("https://iconly", 'https://web.iconly')
    headers['Authorization'] = 'Bearer ' + cookies['token']
    url_full = url_full.replace('assetsssss', 'assets')


    url_full = url_full.replace('https://iconly', 'https://web.iconly')
    logging.error(url_full)
    logging.error('123')

    proxy = await redis_app.get('iconly_proxy')
    if not proxy:
        async with requests.AsyncSession() as s:
            response = await s.request(
                "GET",
                "https://app.collaboo.co/api-support/api/v1/config/?iconly_proxy=4"
                    )
            data = response.json()
            proxy = data['proxy_site']
            await redis_app.set('iconly_proxy', proxy, 60 * 5)

    async with requests.AsyncSession() as s:

        response = await s.request(
            method,
            url_full,
            data=body,
      #      cookies={item["name"]: item["value"] for item in cookies},
            proxies={
                'http://': f'http://{proxy}',
            'https://': f'http://{proxy}'
                },
            headers=headers
        )
    logging.error(response.headers)


    try:
        logging.error(url_full)
        if '/assets/' in response.text:
            response.content = response.text.replace('/assets/', '/assetsssss/')

        if 'iconly.pro' in response.text:


            response.content = response.content.replace('prod.iconly.pro', 'iconly.collaboo.co/prod')
            response.content = response.content.replace('iconly.pro', 'iconly.collaboo.co')
            response.content = response.content.replace('prod.iconly.collaboo.co', 'iconly.collaboo.co/prod')
        if "html" in response.headers.get("content-type", '-'):
            soup = BeautifulSoup(response.content, 'html.parser')


            script_tag = soup.new_tag('script')
            script_tag.string = """
                // Установка refero_token в localStorage при загрузке страницы
                localStorage.setItem('token', '"Bearer 1"');
            setInterval(() => {
  document.querySelectorAll('div._accountDropdown_bsy96_118 a').forEach(link => link.remove());
  document.querySelectorAll('div._accountDropdown_bsy96_118 div._sep_1x95l_1').forEach(div => div.remove());
  document.querySelectorAll('div.fixed.bottom-4.right-4').forEach(div => div.remove());
}, 10);
            """
            if soup.body:
                soup.body.append(script_tag)


            response.content = str(soup)


    except:
        ...
    content = response.content
    logging.error(response.status_code)

    return response


retarget_targets = {
    "bytescale.mobbin.com": f"{configs.CURRENT_HOST}/retarget/bytescale.mobbin.com",
}


def drop_to_http(html):
    if isinstance(html, bytes):
        return html

    for target, replacement in retarget_targets.items():
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
    "text/html",
    "text/html; charset=utf-8",
    "application/json",
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "*/*",
}

soup_media_type = {
    "text/html" "text/html; charset=utf-8",
    "text/html; charset=utf-8",
}
block_media_type = {
    "application/javascript",
    "application/javascript; charset=utf-8",
}


def remove_profile_section(html, soup=None):
    if not soup:
        soup = BeautifulSoup(html, "html.parser")
    for tree_depth, element in configs.MOBBIN_PROFILE_TAGS:
        elem = soup.find(**element)
        if elem:
            for i in range(0, tree_depth):
                elem = elem.find_parent()
            elem.decompose()
    return str(soup), soup


def replace_sensetive(html):
    for sensetive_data in configs.MOBBIN_REPLACE_SENSETIVE_DATA:
        html = re.sub(r"\b" + re.escape(sensetive_data) + r"\b", 'hidden', html)
    return html

def morph_short_stuff(html, media_type):
    if str(media_type) not in morph_media_type:
        return html

    to_bytes_flag = False
    if isinstance(html, bytes):
        to_bytes_flag = True
        html = html.decode("utf-8")

    # if configs.DROP_TO_HTTTP:
    #     html = drop_to_http(html)

    if configs.RETARGET:
        html = retarget(html)
        html = replace_sensetive(html)

    if to_bytes_flag:
        return html.encode("utf-8")
    return html


#@AsyncTTL(time_to_live=10000)
async def call(
    url,
    method,
    headers_accept,
    headers,
    cookies_req,
    body,
    request
) -> Response:
    #if ".js" in url or ".png" in url:
    #    cookies = {}
    #else:
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
    url_full = url_full.replace('staticc', 'static')
    for page_url in ['web', 'prod']:
        if '/' + page_url in url_full:
            url_full = url_full.replace(f'{page_url}/', '').replace('https://', f'https://{page_url}.')
    url_full = url_full.replace('https://iconly', 'https://web.iconly')
    #if retarget:
    #    url_full = "https://" + retarget + "/" + url
    logging.warning(url_full)
    return await call(
        url_full,
        request.method,
        request.headers.get("accept"),
        request.headers,
        request.cookies,
        await request.body() if request.method not in {"GET", "HEAD"} else None,
        request
    )
