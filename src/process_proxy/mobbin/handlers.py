import re
import asyncio
from typing import Optional
import logging

from fastapi import Response, Request, HTTPException

from starlette.responses import RedirectResponse



from curl_cffi import requests

from bs4 import BeautifulSoup

import cloudscraper


from src.process_proxy.mobbin.login import login, load_cookies

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
    if "chunksss" in url_full:
        url_full = url_full.replace('chunksss', "chunks")
    headers = {k: v for k, v in request.headers.items()}
    headers['host'] = "mobbin.com"
    if headers.get('referer'):
        del headers['referer']
    if headers.get('origin'):
        del headers['origin']
    if headers.get('cookie'):
        del headers['cookie']

    if "login" in url_full:
        cookies_res = await login()
        return await proxy_request([{"name": k, "value": v} for k,v in cookies_res.items()], "https://mobbin.com/discover/apps/ios/latest", method, body, request)

    async with requests.AsyncSession() as s:
        response = await s.request(
            method,
            url_full,
            data=body,
            cookies={item["name"]: item["value"] for item in cookies},
            headers=headers
        )

    content = response.content
    if "html" in response.headers.get("content-type", '-'):
        if 'Discover real-world design inspiration.' in response.text:
            cookies_res = await login()
            return await proxy_request([{"name": k, "value": v} for k,v in cookies_res.items()], url_full, method, body, request)

        response.content = response.text.replace('static/chunks', 'static/chunksss')
        soup = BeautifulSoup(response.content, 'html.parser')
        style_tag = soup.new_tag("style")
   #     style_tag.string = f'span[aria-label="Avatar of BJ"]' + "{display: none;}"
        style_tag.string = ".max-h-\[--radix-dropdown-menu-content-available-height\].overflow-y-auto > div:not(:nth-child(8)) {display: none;}"
        try:
            soup.head.append(style_tag)
        except Exception as ex:
            logging.error(f"{response.content}, {response.status_code}")
        response.content = str(soup)
    # if response.status_code == 403:
    #     logging.info(f"info: {response.text}")
    #     cookies_res = await login()
    #     return await proxy_request([{"name": k, "value": v} for k,v in cookies_res.items()], url_full, method, body, request)
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
    cookies = await load_cookies()

    resp = await proxy_request(cookies, url, method, body, request)

    return resp


async def proxy_call(
    request: Request,
    url: str,
    retarget: Optional[str] = None,
) -> Response:
    if not is_request_allowed(url, request.method):
        raise HTTPException(403)
    if url in ["", "/"]:
        return RedirectResponse("https://mobbin.collaboo.co/discover/apps/ios/latest")
    if str(request.query_params):
        url = url + "?" + str(request.query_params)
        if "section=key_screen" in url:
            url += "&_rsc=2adx5"

    url_full = "https://" + configs.TARGET_HOST + "/" + url
    if retarget:
        url_full = "https://" + retarget + "/" + url
    return await call(
        url_full,
        request.method,
        request.headers.get("accept"),
        request.headers,
        request.cookies,
        await request.body() if request.method not in {"GET", "HEAD"} else None,
        request
    )
