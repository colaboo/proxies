import logging
from twocaptcha import TwoCaptcha


async def solve_captcha(api_key: str,
                                  page_url: str, proxy: str = None,
                                  timeout: int = 300) -> str:
    solver = TwoCaptcha(api_key)
    try:
        result = solver.turnstile(
            sitekey='0x4AAAAAABQ3CCKaTml7wReF',
            url=page_url,
        )

    except Exception as e:
        logging.error(e)
        return ""
    return result["code"]
