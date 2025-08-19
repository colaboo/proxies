from functools import partial
from typing import Any, TypeVar, Annotated


from pydantic import AfterValidator


T = TypeVar("T")

LABEL_RESONABLE_SIZE = 150
SMALL_RESONABLE_SIZE = 500
MEDIUM_RESONABLE_SIZE = 5_000
LARGE_RESONABLE_SIZE = 50_000


def reasonable_size(size: int, value: T) -> T:
    if len(value) <= size:
        return value
    raise ValueError("Size is out of bounds")


def positive(value: T) -> T:
    if value < 0:
        raise ValueError("Must be positive")
    return value


label_size = partial(reasonable_size, LABEL_RESONABLE_SIZE)
small_size = partial(reasonable_size, SMALL_RESONABLE_SIZE)
medium_size = partial(reasonable_size, MEDIUM_RESONABLE_SIZE)
large_size = partial(reasonable_size, LARGE_RESONABLE_SIZE)


LabelText = Annotated[str, AfterValidator(label_size)]
SmallText = Annotated[str, AfterValidator(small_size)]
MediumText = Annotated[str, AfterValidator(medium_size)]
PosInt = Annotated[int, AfterValidator(positive)]
PosFloat = Annotated[float, AfterValidator(positive)]
