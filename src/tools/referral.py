from itertools import accumulate
from functools import reduce

from core.configs import configs


async def proc_free_transactions(
    free_transactions,
    profile,
):
    referrer_percent = 100 / profile.referrer_percent

    def acc(x, y):
        x.amount_usd += y.amount_usd * referrer_percent
        return x

    return reduce(
        acc,
        free_transactions,
    ).amount_usd
