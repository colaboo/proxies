import logging

from urllib.parse import quote

from aiohttp import ClientSession


from src.core.configs import configs


from src.tools.exceptions_shortcuts import ApiException


from cache import AsyncTTL


# @AsyncTTL(time_to_live=1000)
async def get_user_proxy_relation(
    user_id: str,
    proxy: str,
):
    async with ClientSession() as session:
        async with session.get(
            configs.SUBS_HOST + "/api-subs/api/v1/sub-user/internal/access",
            params={
                "proxy": proxy,
                "user_id": user_id,
            },
            headers={
                "X-Internal-Auth": configs.SIMPLE_SERVER_AUTH_KEY,
            },
        ) as resp:
            if resp.ok:
                return await resp.json()
            if resp.start != 404:
                logging.exception(await resp.text())
                raise ApiException()
