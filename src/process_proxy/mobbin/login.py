import json
import logging
from curl_cffi import requests
from fastapi import HTTPException
import asyncio
from src.process_proxy.mobbin.captcha import solve_captcha
from src.process_proxy.mobbin.sse_decoder import parse_sse_response

lock = False

async def load_cookies():
    content = []

    with open("keys/mobbin_cookies.json", "r") as file:
        content = json.load(file)
    # while content == [] and tries >= 0:
    #     await login()
    #     with open("keys/mobbin_cookies.json", "r") as file:
    #         content = json.load(file)
    #     tries -= 1
    # if content == []:
    #     raise HTTPException(403)
    return content

async def login() -> dict[str, str]:
    global lock
    if lock == True:
        return {}
    lock = True
    logging.info("Logging to mobbin.com")
    cookies_res = {}

    headers = {
'accept': 'text/x-component',
'accept-language': 'ru,en;q=0.9,en-GB;q=0.8,en-US;q=0.7',
'baggage': 'sentry-environment=production,sentry-release=54a6b90f38c1ee0bf9508880ed273d8418d51213,sentry-public_key=63305a18ca734bc0a55af2981c0d4d0a,sentry-trace_id=7825ca855e59448896340435b3564fbc,sentry-org_id=4504042693591040,sentry-sampled=false,sentry-sample_rand=0.8222276149897392,sentry-sample_rate=0.001',
'content-type': 'text/plain;charset=UTF-8',
'next-action': '652456ea57359bb8849f2c64654cf258fa240cdc',
'next-router-state-tree': '%5B%22%22%2C%7B%22children%22%3A%5B%22(auth)%22%2C%7B%22children%22%3A%5B%22(suspense)%22%2C%7B%22children%22%3A%5B%22login%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2C%22%2Flogin%22%2C%22refresh%22%5D%7D%5D%7D%5D%7D%5D%7D%2Cnull%2Cnull%2Ctrue%5D',
'origin': 'https://mobbin.com',
'priority': 'u=1, i',
'referer': 'https://mobbin.com/login',
'sec-ch-ua': '"Microsoft Edge";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
'sec-ch-ua-mobile': '?1',
'sec-ch-ua-platform': '"Android"',
'sec-fetch-dest': 'empty',
'sec-fetch-mode': 'cors',
'sec-fetch-site': 'same-origin',
'sentry-trace': '7825ca855e59448896340435b3564fbc-a668b99f1a47abcb-0',
'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36 Edg/137.0.0.0',
# 'cookie': '_pin_unauth=dWlkPVltRTNNR1EyTkRrdFptUXpNeTAwT1RBNUxXSXhaVEF0WXpFeVlqRXlaV1l6TldKaA; __stripe_mid=d571026a-2d43-4d81-8f7a-187db9f6d4f3594351; _gcl_au=1.1.1744753862.1747474894.1612265829.1747841341.1747841910; _fbp=fb.1.1747842664197.467906840764043429; ajs_anonymous_id=7ff70efb-1dee-4a69-ac8d-b774d9a18574; ajs_user_id=6fc9b6b5-b615-4d7a-8a5a-91085103bc94; _gid=GA1.2.1577374247.1749796505; _gat_UA-114922841-1=1; __stripe_sid=a4d4d462-2a5d-4a45-9bd0-c48917579410b55a55; _ga=GA1.2.1108519323.1747474894; _ga_H2L379YHME=GS2.1.s1749796504$o3$g1$t1749796531$j33$l0$h0',
}
    submit_headers = {
        "next-action": "345bbc1d88a07588f0f3331a1549a5a4b1092324"
    }

    params = {
        'redirect_to': '/settings/account',
    }


    async with requests.AsyncSession() as s:
        response = await s.post('https://mobbin.com/login', params=params, cookies=cookies_res, headers=headers, data=data)
        if response.text != "":
            events = parse_sse_response(response.text)
            for event in events:
                if isinstance(event["data"], dict) and event["data"].get("rateLimited") != None:
                    challenge = event['data']['rateLimited']['challenge']
                    challenge_url = f'https://mobbin.com/{challenge}'
                    logging.info(f"Get captcha! Challenge: {challenge}.")
                    cf_token = await solve_captcha("7d218cfd86add9e2befca4ada6475cc7", challenge_url)
                    submit_payload = json.dumps([challenge, cf_token, "/"])
                    submit_resp = await s.post(challenge_url, headers=submit_headers, data=submit_payload)
                    if submit_resp.status_code == 303:
                        logging.info("URA GOTOVO!!!")
                    break
        response = await s.post('https://mobbin.com/login', params=params, cookies=cookies_res, headers=headers, data=data)
        cookies_res = {k: v for k, v in response.cookies.items()}
        logging.error("Cookies updated.")
        with open("keys/mobbin_cookies.json", "w") as f:
            f.write(json.dumps([{"name": k, "value": v} for k, v in cookies_res.items()]))
    return cookies_res
