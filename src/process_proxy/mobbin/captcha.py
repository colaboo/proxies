import logging
from twocaptcha import TwoCaptcha


async def solve_captcha(api_key: str,
                                  page_url: str, proxy: str = None,
                                  timeout: int = 300) -> str:
    solver = TwoCaptcha(api_key)
    result = solver.turnstile(
            sitekey='0x4AAAAAABQ3CCKaTml7wReF',
            url=page_url,
        )
    return result["code"]
