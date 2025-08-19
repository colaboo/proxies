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


from curl_cffi import requests

from bs4 import BeautifulSoup

from cache import AsyncTTL

import cloudscraper


from src.tools.proxy import inject_heartbeat

from src.process_proxy.flaticon.login import login

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

    page = splitted[0].split('?')[0]
    if page in ['pricing', 'profile', 'merchandising-license']:

        return False

    if len(page) < 5 and len(splitted) > 1:
        if splitted[1].split('?')[0] in ['pricing', 'profile', 'merchandising-license']:
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
    request
) -> Response:
    headers = {k: v for k, v in request.headers.items()}
    headers['host'] = "www.flaticon.com"
    if headers.get('referer'):
        del headers['referer']
    if headers.get('cookie'):
       del headers['cookie']


    #
    response = requests.request(
            method,
            url_full,
           cookies=cookies,
           headers=headers,
           data=body,
        )
    #
    #
    try:
        if "flaticon" in response.text:
            response.content = response.text.replace('media.flaticon.com', 'flaticon.collaboo.co/mediaaa_flaticon')
            response.content = response.text.replace('www.flaticon.com', 'flaticon.collaboo.co')
        #    response.content = response.content.replace('https://localhost:8000', 'http://localhost:8000')
    #         response.content = response.text.replace('cdn-front.freepik.com', 'dev-freepik.collaboo.co/cdn_front')
    #         response.content = response.content.replace('img.freepik.com', 'dev-freepik.collaboo.co/image_caches')
    #         response.content = response.content.replace('www.freepik.com', 'dev-freepik.collaboo.co')
    #         response.content = response.content.replace('static.cdnpk.net', 'dev-freepik.collaboo.co/static_cdnpk')
    #         response.content = response.content.replace('pikaso.cdnpk.net', 'dev-freepik.collaboo.co/pikaso_cdnpk')
    #         response.content = response.content.replace('https://pikaso-chat.freepik.${window.location.hostname.endsWith(".com")?"com":"es"}', 'https://dev-freepik.collaboo.co/pikaso_chat')
    #         response.content = response.content.replace('"pikaso-data.freepik."+(sl?"com":"es")', '"dev-freepik.collaboo.co/pikaso_data"')
    #         response.content = response.content.replace('"pikaso-data.freepik."+(window.location.hostname.endsWith(".com")?"com":"es")', '"dev-freepik.collaboo.co/pikaso_data"')
    #    #     response.content = response.content.replace('https://accounts.google.com/gsi/client', '/static_cdnpk/_next/static/chunks/5730-7db00727049b9834.js')
    #     #    response.content = response.content.replace('document.body.appendChild(g)', '')
    except:
        ...
    try:
        if "html" in response.headers.get("content-type", '-'):
            soup = BeautifulSoup(response.content, 'html.parser')
            style_tag = soup.new_tag("style")
            style_tag.string = 'span[data-track-arguments="ga, event, menu, click, more"] {display: none;}'
            soup.head.append(style_tag)
            style_tag = soup.new_tag("style")
            style_tag.string = '.link-pricing {display: none;}'
            soup.head.append(style_tag)
            style_tag = soup.new_tag("style")
            style_tag.string = '.header--menu__login {display: none;}'
            soup.head.append(style_tag)
            style_tag = soup.new_tag("style")
            style_tag.string = 'div[aria-label="Cookie banner"] {display: none;}'
            soup.head.append(style_tag)
            script_tag = soup.new_tag('script')

            script_tag.string = """
                // Установка refero_token в localStorage при загрузке страницы
                localStorage.setItem('token', '"Bearer 1"');
            setInterval(() => {
  document.querySelectorAll('div.header--menu__login').forEach(link => link.remove());
  document.querySelectorAll('li.link-pricing').forEach(link => link.remove());
  document.querySelectorAll('span[data-track-arguments="ga, event, menu, click, more"]').forEach(div => div.remove());
}, 10);
            """
            if soup.body:
                soup.body.append(script_tag)
            response.content = str(soup)
    except:
        ...
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

    if configs.DROP_TO_HTTTP:
        html = drop_to_http(html)

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

    url_full = "https://" + "www.flaticon.com" + "/" + url
    if retarget:
        url_full = "https://" + retarget + "/" + url
    url_full = url_full.replace(':433', '')
    if "mediaaa_flaticon" in url_full:
        url_full = url_full.replace('mediaaa_flaticon/', '')
        url_full = url_full.replace('www.', 'media.')
    logging.warning(f"{url_full=}")
    return await call(
        url_full,
        request.method,
        request.headers.get("accept"),
        request.headers,
        request.cookies,
        await request.body() if request.method not in {"GET", "HEAD"} else None,
        request
    )
