from functools import partial
from typing import Any, TypeVar


from core.configs import configs


T = TypeVar("T")


with open(configs.path_to_ban_words, "r") as file:
    banned_words = {line.strip() for line in file}


def dont_have_bad_words(
    value: T,
) -> T:
    if any(word in value.lower() for word in banned_words):
        raise ValueError("Bad words")
    return value
