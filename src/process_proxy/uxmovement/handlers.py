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


from tools.proxy import inject_heartbeat

from process_proxy.uxmovement.login import login

# from tools.file import dump_to_file
from core.configs import configs


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
) -> Response:
    async with requests.AsyncSession() as s:
        response = await s.request(
            method,
            url_full,
            data=body,
            cookies={item["name"]: item["value"] for item in cookies},
        )
    content = response.content
    if "html" in response.headers.get('content-type', ''):
        soup = BeautifulSoup(content, "html.parser")
        for url in ['/chat', '/about', 'leaderboard']:
            style_tag = soup.new_tag("style")
            style_tag.string = f"a[href='{url}'] { '{display: none;}' }"
            soup.head.append(style_tag)
        style_tag = soup.new_tag("style")
        style_tag.string = 'button[data-testid="noncontributor-cta-button"] { display: none; }'
        soup.head.append(style_tag)
        style_tag = soup.new_tag("style")
        style_tag.string = 'div[id="discussion"] { display: none; } .comments-page{ display: none; } .cookieBanner-fZ6hup {display: none}'
        soup.head.append(style_tag)
        content = soup.prettify()
    return (content, response.headers.get("content-type"))


retarget_targets = {
    # "substack.com": f"{configs.CURRENT_HOST}",
    "uxmovement.substack.com": "uxmove.collaboo.co",
    "substackcdn.com": "uxmove.collaboo.co",
    "substack.com": "nourl",
    "uxmove.collaboo.co/bundle": "uxmove.collaboo.co/retarget/substackcdn.com%2Fbundle",
    "uxmove.collaboo.co/image": "uxmove.collaboo.co/retarget/substackcdn.com%2Fimage",
    "uxmove.collaboo.co/static": "uxmove.collaboo.co/retarget/substackcdn.com%2Fstatic",
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
) -> Response:
    cookies = await asyncio.to_thread(login)
    resp = await proxy_request(cookies, url, method, body)
    return Response(morph_short_stuff(*resp), media_type=resp[1])


async def proxy_call(
    request: Request,
    url: str,
    retarget: Optional[str] = None,
) -> Response:
    if not is_request_allowed(url, request.method):
        raise HTTPException(403)
    if str(request.query_params):
        url = url + "?" + str(request.query_params)
    url_full = "https://uxmovement.substack.com/" + url
    if retarget:
        url_full = "https://" + retarget + "/" + url
    return await call(
        url_full,
        request.method,
        request.headers.get("accept"),
        await request.body() if request.method not in {"GET", "HEAD"} else None,
    )
