import time


cache = {}


def variable_ttl_cache(cache_item: dict, default_ttl: int = 10000):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            value = cache_item.get(key)
            if value and value[0] > time.time():
                return value[1]
            ttl, res = await func(*args, **kwargs)
            cache_item[key] = (time.time() + ttl, res)
            return res

        return wrapper

    return decorator
