from aiohttp import ClientSession


from cache import AsyncTTL


@AsyncTTL(time_to_live=60 * 60 * 12, maxsize=1024)
async def usd_ru():
    async with ClientSession() as session:
        async with session.get(
            "https://v6.exchangerate-api.com/v6/4e6372e0a8387231bf5bcd9d/pair/USD/RUB"
        ) as resp:
            data = await resp.json()
            return data["conversion_rate"]
