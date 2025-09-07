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


from tools.proxy import inject_heartbeat

from process_proxy.freepik.login import login

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
    if splitted[0].split('?')[0] in ['pricing', 'user']:
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
    headers['host'] = "www.freepik.com"
    if headers.get('referer'):
        del headers['referer']
    if headers.get('cookie'):
        del headers['cookie']



    kwargs = {
            'data': body,
            'headers': headers
            }
    #kwargs = {}
    logging.error(f"{url_full=}")
    logging.error(request.cookies)

    if "img" in url_full or "cdn-front" in url_full or "static.cdnpk.net" in url_full:
        kwargs = {}
    if "pikaso.cdnpk" in url_full:
        kwargs = {}
        cookies = {}
        if "%3" in url_full:
            url_full = url_full.replace('%3D', '=')
    if "pikaso-chat" in url_full or "pikaso-data" in url_full:
        json_str = body.decode('utf-8')
        kwargs = {'json':json.loads(json_str),
                  'timeout':1000
                  }
    if "action=download" in url_full or ("download" in url_full and "api" in url_full):
        url_full += "&walletId=ff5bcb6b-33c2-49b6-8570-28d9f24c9a34"
    url_full = url_full.replace('serega', '')
    async with requests.AsyncSession() as s:

        response = await s.request(
            method,
            url_full,

           cookies=cookies,

            **kwargs
        )



    logging.error(response.status_code)
    logging.error(kwargs)
    logging.error(url_full)
    try:
        is_text = False
        if "freepik.com" in response.text:
            is_text = True

            response.content = response.text.replace('cdn-front.freepik.com', 'freepik.collaboo.co/cdn_front')
           # response.content = response.content.replace('chunks/', 'chunksserega/')
            response.content = response.content.replace('img.freepik.com', 'freepik.collaboo.co/image_caches')
            response.content = response.content.replace('www.freepik.com', 'freepik.collaboo.co')
            response.content = response.content.replace('static.cdnpk.net', 'freepik.collaboo.co/static_cdnpkkkkk')
            response.content = response.content.replace('pikaso.cdnpk.net', 'freepik.collaboo.co/pikaso_cdnpk')
            response.content = response.content.replace('https://pikaso-chat.freepik.${window.location.hostname.endsWith(".com")?"com":"es"}', 'https://freepik.collaboo.co/pikaso_chat')
            response.content = response.content.replace('"pikaso-data.freepik."+(sl?"com":"es")', '"freepik.collaboo.co/pikaso_data"')
            response.content = response.content.replace('"pikaso-data.freepik."+(window.location.hostname.endsWith(".com")?"com":"es")', '"freepik.collaboo.co/pikaso_data"')
            response.content = response.content.replace('https://cdn-ukwest.onetrust.com/scripttemplates/otSDKStub.js', '')
       #     response.content = response.content.replace('https://dev-freepik.collaboo.co/static_cdnpk/_next/static/chunks/pages/_app-f4cbd7edfafc5cc7.js', '')
       #     response.content = response.content.replace('https://accounts.google.com/gsi/client', '/static_cdnpk/_next/static/chunks/5730-7db00727049b9834.js')
        #    response.content = response.content.replace('document.body.appendChild(g)', '')
        if "w3.org" in response.text:
            is_text = True
            if not is_text:
                response.content = response.text
            #response.content = response.content.replace('M486.2 50.2c-9.6-3.8-20.5-1.3-27.5 6.2l-98.2 125.5-83-161.1C273 13.2 264.9 8.5 256 8.5s-17.1 4.7-21.5 12.3l-83 161.1L53.3 56.5c-7-7.5-17.9-10-27.5-6.2C16.3 54 10 63.2 10 73.5v333c0 35.8 29.2 65 65 65h362c35.8 0 65-29.2 65-65v-333c0-10.3-6.3-19.5-15.8-23.3', 'M504.688 344.692 345.092 504.688c-4.9 4.899-11.3 7.399-17.7 7.399s-12.8-2.4-17.6-7.299L209.695 403.99c-9.8-9.7-9.8-25.599-.1-35.399s25.599-9.8 35.399-.1l82.398 83.098 141.896-142.297c9.8-9.799 25.6-9.799 35.4-.1 9.699 9.9 9.799 25.7 0 35.5m-330.492 94.497c-29.1-29.199-29.2-76.598-.1-105.897 29.199-29.299 76.798-29.399 106.097-.2l.2.2 46.999 47.399 106.397-106.698c8-8.1 17.6-14.099 28.1-17.799V64.998c0-10.3-5.9-19.5-14.8-23.199-9-3.8-19.2-1.3-25.799 6.2l-91.998 125.597L251.194 12.3c-4.2-7.6-11.8-12.3-20.2-12.3s-16.099 4.7-20.199 12.3l-78.198 160.696L40.599 47.899c-6.6-7.5-16.8-10-25.8-6.2C5.9 45.399 0 54.599 0 64.899V389.79c0 39.899 32.3 72.199 72.198 72.199h124.697z')
            logging.error('123123')

        if "text-premium-gold-500" in response.text:
            if not is_text:
                response.content = response.text
            response.content = response.content.replace('text-premium-gold-500', 'h')

    except:
        ...
    try:
        if "html" not in response.headers.get("content-type", '-'):
            raise Exception()
        soup = BeautifulSoup(response.content, 'html.parser')
        script_code = """
<script>
function myFunction() {
    var btn = document.querySelector('button[data-cy="go-premium-download"]');
    if (btn) {
                btn.classList.remove('text-premium-gold-700');
            btn.classList.add('text-surface-foreground-3');
            btn.textContent = 'Download';
        // Переопределяем обработчик onclick
        btn.onclick = function() {
            event.stopPropagation();
                        var currentUrl = window.location.href.replace('dev-freepik.collaboo.co/', 'www.freepik.com/');

            // Отправляем POST-запрос
        fetch('https://dev-freepik.collaboo.co/download_freepik', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url: currentUrl })
            }).then(response => response.json())
            .then(data => {

                    // Открываем ссылку для скачивания
                    window.location.href = data.url;
            })
            // Можно добавить свою логику здесь
        };
    }
};
setInterval(myFunction, 1000);
</script>
"""
        soup.head.append(BeautifulSoup(script_code, 'html.parser'))
        script_tag = soup.new_tag('script')
        script_tag.string = """
                // Установка refero_token в localStorage при загрузке страницы
                localStorage.setItem('token', '"Bearer 1"');
            setInterval(() => {
  document.querySelectorAll('a[href="/pricing?origin=freepik_web"]').forEach(link => link.remove());
  document.querySelectorAll('a[data-cy="signin-button"]').forEach(div => div.remove());
document.querySelectorAll('button').forEach(function(button) {
    if (button.textContent.trim() === 'Projects' || button.textContent.trim() == "AI Suite") {
        button.style.display = 'none';
    }
});
document.querySelectorAll('section').forEach(function(button) {
    if (button.textContent.trim().includes("Here's where you left off")) {
        button.style.display = 'none';
    }
});
document.querySelectorAll('div.mx-auto').forEach(function(button) {
    if (button.textContent.trim().includes("Cover it all, from AI and editing tools to stock content!")) {
        button.style.display = 'none';
    }
});
document.querySelectorAll('div.mx-auto.flex.max-w-screen-2xl.flex-col').forEach(div => div.remove());
}, 10);
            """
        if soup.body:
            soup.body.append(script_tag)
        response.content = soup.prettify()

    except:
        ...
    try:
        logging.error("gsi/client" in response.text)
        logging.error('123')
        if "https://accounts.google.com/gsi/client" in response.text:
            response.content = response.text.replace('https://accounts.google.com/gsi/client', 'https://freepik.collaboo.co/static_cdnpk/_next/static/chunks/5316-8a5182400312a53c.js')
    except:
        ...
    try:

        logging.error('"undefined"!=typeof window' in response.text)
        if '"undefined"!=typeof window' in response.text:
            response.content = response.text.replace('"undefined"!=typeof window', ' true')
    except:
        ...
    try:
        if "n.permissions.canDownloadResourcePremium" in response.text:
            response.content = response.content.replace('n.permissions.canDownloadResourcePremium', 'true')
            response.content = response.content.replace('null==n', 'null==null')
            response.content = response.content.replace('!!(null==null?void 0:true)', ' true')
    except:
        ...
    GR_TOKEN = response.cookies.get('GR_TOKEN')
    GR_REFRESH = response.cookies.get('GR_REFRESH')
    if GR_TOKEN and GR_REFRESH:
        import json
        with open("keys/freepik_cookies.json", "r") as f:
            data = json.loads(f.read())
        data['GR_TOKEN'] = GR_TOKEN
        data['GR_REFRESH'] = GR_REFRESH
        with open("keys/freepik_cookies.json", "w") as f:
            data = f.write(json.dumps(data))
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

    url_full = "https://www.freepik.com/" + url
    if url_full == "https://www.freepik.com/":
        url_full = "https://www.freepik.com/search"
    if retarget:
        url_full = "https://" + retarget + "/" + url
    if "cdn_front" in url_full:
        url_full = "https://cdn-front.freepik.com" + url_full.split('cdn_front')[1]
    if "image_caches" in url_full:
        url_full = "https://img.freepik.com" + url_full.split('image_caches')[1]
    if "static_cdnpkkkk" in url_full:
        url_full = "https://static.cdnpk.net" + url_full.split('static_cdnpkkkkk')[1]
    if "pikaso_cdnpk" in url_full:
        url_full = "https://pikaso.cdnpk.net" + url_full.split('pikaso_cdnpk')[1]
    if "pikaso_chat" in url_full:
        url_full = "https://pikaso-chat.freepik.com" + url_full.split('pikaso_chat')[1]
    if "pikaso_data" in url_full:
        url_full = "https://pikaso-data.freepik.com" + url_full.split('pikaso_data')[1]
    url_full = url_full.replace(':433', '')
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
