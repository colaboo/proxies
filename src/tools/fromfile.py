import logging

from typing import Optional, Any


import toml

from pydantic import BaseModel


from tools.exceptions import (
    get_exception_id,
    ExceptionMessage,
)

# from core.configs import configs


class PromptNotFoundError(Exception):
    pass


class FromTomlFile(BaseModel):
    def __init__(self, path: str, *args, **kwargs):
        try:
            with open(path, "r") as file:
                loaded_data = toml.load(file).get(self.__class__.__name__)
                return super().__init__(**loaded_data)
        except FileNotFoundError:
            raise PromptNotFoundError

    def get(
        self,
        key: str,
        default: Optional[Any] = None,
    ):
        # if configs.DEBUG:
        #     logging.info(f"From-toml-file key: {key}")
        return self.model_dump().get(key, default)


ORIGIN = "PROMPTSTORAGE"

exceptions = {
    PromptNotFoundError: ExceptionMessage(
        id=get_exception_id(f"{ORIGIN}", "promptnotfound"),
        status=404,
        title="prompt storage: prompt for this topic not found",
    ),
}
