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


from seleniumbase import Driver

import requests as requests_base
from curl_cffi import requests

from bs4 import BeautifulSoup

from cache import AsyncTTL

import cloudscraper
from redis.asyncio import Redis

from src.tools.proxy import inject_heartbeat

from src.process_proxy.refero.login import login

# from src.tools.file import dump_to_file
from src.core.configs import configs
redis_app = Redis(
    host="redis",
    port=6379,
)

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
    if url.split('?')[0] in ["/billing", "billing", "/pricing", "pricing"]:
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
    headers['host'] = "refero.design"
    if headers.get('referer'):
        del headers['referer']
    if headers.get('cookie'):
        del headers['cookie']

    logging.error(url_full)
#    if headers.get('x-real-ip'):
#        del headers['x-real-ip']
#    if headers.get('x-forwarded-for'):
#        del headers['x-forwarded-for']
#    if headers.get('cf-connecting-ip'):
#        del headers['cf-connecting-ip']
    logging.error(headers)
    if not headers:
        headers = {}

    headers['authorization'] = 'Bearer ' + cookies['refero_token']

    logging.error(headers)
   # await redis_app.set(f"proxy__{configs.TARGET_HOST}", "")
   # if await redis_app.get(f"proxy__{configs.TARGET_HOST}"):
   #     proxy = await redis_app.get(f"proxy__{configs.TARGET_HOST}")
   #     proxy = proxy.decode()
   # else:
   #     resp = requests.request("GET", "https://app.collaboo.co/api-support/api/v1/config/")
   #     proxy = resp.json()['proxy']
   #     await redis_app.set(f"proxy__{configs.TARGET_HOST}", proxy, 60 * 5)
    #proxy = "bfMEdNzQ:2MDpKPp4@166.1.191.155:63560"
   # logging.error(f"{proxy=}")
    proxies = {
                 'https': f'socks5h://127.0.0.1:9050',
     'http': f'socks5h://127.0.0.1:9050'
            }
    logging.error(url_full)
    if '.refero' in url_full and 'api.r' not in url_full:
        proxies = None
        headers = {
            'authorization': 'Bearer ' + cookies['refero_token']
                }
    logging.error(f"{proxies=}")
    async with requests.AsyncSession() as s:
        response = await s.request(
            method,
            url_full,
            data=body,
      #      cookies={item["name"]: item["value"] for item in cookies},
            headers=headers,

            proxies=proxies
        )
    logging.error(f"{url_full=} {method=} {body=} {headers=}")
    logging.error(response.headers)
    logging.error('123')
    try:
        logging.error(url_full)
        if 'refero.design' in response.text:
            response.content = response.text.replace('static', 'staticc')
            response.content = response.content.replace('https://refero.design/', 'https://refero.collaboo.co/')
            response.content = response.content.replace('https://api.refero.design', 'https://refero.collaboo.co/api')
            response.content = response.content.replace('images.refero.design','refero.collaboo.co/data_images')
            response.content = response.content.replace('refero.design', 'refero.collaboo.co')
            response.content = response.content.replace('images.dev-refero.collaboo.co', 'refero.collaboo.co/data_images')
            response.content = response.content.replace('api.dev-refero.collaboo.co', 'refero.collaboo.co/api')
            logging.error('refero.design' in response.text)
            logging.error("213")
        if "html" in response.headers.get("content-type", '-'):
            soup = BeautifulSoup(response.content, 'html.parser')


            script_tag = soup.new_tag('script')
            script_tag.string = f"""
                // Установка refero_token в localStorage при загрузке страницы
                localStorage.setItem('refero_token', '1');
            """
            if soup.body:
                soup.body.append(script_tag)
            style_tag = soup.new_tag("style")
            style_tag.string = 'a[href="/billing"] {display: none;}'
            soup.head.append(style_tag)
            style_tag = soup.new_tag("style")
            style_tag.string = 'a[href="/pricing"] {display: none;}'
            soup.head.append(style_tag)
            script_tag = soup.new_tag('script')
            script_tag.string = """
setInterval(() => {
document.querySelectorAll('a[href="https://x.com/intent/follow?screen_name=referodesign"]').forEach(a => {
  if (a.parentElement) {


 a.parentElement.style.display = 'none';
 const parent = a.parentElement.parentElement;
 const divs = parent.querySelectorAll('div');

 if (divs.length > 0){
 const lastDiv = divs[divs.length - 1];
 lastDiv.style.display = 'none';
 divs[0].style.display = 'none';
}


 }
});

document.querySelectorAll('a[href="/how-it-works"]').forEach(a => {
a.parentElement.parentElement.parentElement.querySelectorAll('ul').forEach(ul => {
ul.style.display = 'none';
})
})

}, 100
);

"""
            if soup.body:
                soup.body.append(script_tag)
            response.content = str(soup)


    except Exception as e:
        import traceback
        logging.error(traceback.format_exc())
    content = response.content
    logging.error(response.status_code)
    if response.status_code == 503:
        return await proxy_request(cookies, url_full, method, body, request, False)
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
    if "data_images" in url_full:
        url_full = url_full.replace('data_images/', '').replace('https://', 'https://images.')
    if "api/" in url_full:
        url_full = url_full.replace('api/', '').replace('https://', 'https://api.')
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
