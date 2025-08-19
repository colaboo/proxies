from typing import Optional, Tuple

from pydantic import Field, validator, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

import firebase_admin
from firebase_admin import credentials


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="env.sh", env_file_encoding="utf-8")

    DEBUG: Optional[bool] = False

    path_to_firebase_api: str
    FIREBASE_API_KEY: str
    # url_base: str
    DOCS_URL: str = "/docs"
    API_V1_STR: str = "/api/v1"

    # TODO: move to some more secure way in case of moving services to different machines
    SIMPLE_SERVER_AUTH_KEY: Optional[str] = (
        "KEYFORTEST"  # just a string shared between multiple servers to auth between server only requests
    )

    PROJECT_NAME: str = "Proxy"
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost",
        "https://localhost",
        "https://app.collaboo.co",
        "https://mobbin.collaboo.co",
        "https://uxmovements.collaboo.co",
    ]

    CURRENT_HOST: str = "127.0.0.1:8881"
    PROXY_TARGET: str = "http://localhost:8881"
    TARGET_HOST: str = "mobbin.com"

    SUBS_HOST: str = "http://stocks-subs:8000"

    # POSTGRES_DB: Optional[str] = 'postgres'
    # POSTGRES_USER: Optional[str] = 'postgres'
    # POSTGRES_HOST: Optional[str] = 'postgres'
    # POSTGRES_PASSWORD: Optional[str] = 'postgres'

    USE_FIREBASE_AUTH: Optional[bool] = True
    RETARGET: Optional[bool] = True
    DROP_TO_HTTTP: Optional[bool] = True

    MOBBIN_PROXY: Optional[str] = "http://localhost:8881"
    MOBBIN_PROFILE_TAGS: Optional[list[Tuple[int, dict]]] = [
        (4, {"id": "radix-:r9:"}),
        (4, {"data-sentry-component": "Avatar"}),
        (4, {"data-sentry-source-file": "Avatar.tsx"}),
        (2, {"id": "radix-:rn:"}),
        (2, {"data-sentry-source-file": "GlobalDropdownMenu.tsx"}),
    ]
    MOBBIN_REPLACE_SENSETIVE_DATA: Optional[list[str]] = [
        "myortv@proton.me",
        "Мёртв уже",
        "Мёртв Уже",
        "Мёртв",
        "myortv.1@gmail.com",
    ]

    UXMOVEMENT_PROXY: Optional[str] = "http://localhost:8882"
    UXMOVEMENT_REPLACE_SENSETIVE_DATA: Optional[list[str]] = [
        "myortv@proton.me",
    ]
    UXMOVEMENT_REMOVE_TAGS: Optional[list[Tuple[int, dict]]] = [
        # (1, {"id": "trigger48961"}),
        # (1, {"id": "trigger1"}),
        # (1, {"id": "trigger48963"}),
        # (1, {"id": "trigger3"}),
        # (0, {"class": "pencraft pc-reset pencraft buttonBase-GK1x3M buttonText-X0uSmG buttonStyle-r7yGCK priority_primary-RfbeYt size_md-gCDS3o"}),
        # (0, {"class": "pencraft pc-reset pencraft buttonBase-GK1x3M buttonText-X0uSmG buttonStyle-r7yGCK priority_primary-RfbeYt size_md-gCDS3o"}),
        # (0, {"id": "trigger48965"}),
        # (0, {"id": "trigger5"}),
        # (5, {"class": "lucide lucide-message-circle"}),
    ]
    REFERO_PROXY: Optional[str] = "http://localhost:8883"
    ICONLY_PROXY: Optional[str] = "http://localhost:8885"
    CRAFTWORK_PROXY: Optional[str] = "http://localhost:8886"
    FLATICON_PROXY: Optional[str] = "http://localhost:8887"
    FREEPIK_PROXY: Optional[str] = "http://localhost:8888"
    ENVATO_PROXY: Optional[str] = "http://localhost:8889"
    ENVATO_LABS_PROXY: Optional[str] = "http://localhost:8884"

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)


configs = Settings()

firebase_cred = credentials.Certificate(
    configs.path_to_firebase_api,
)
firebase_app = firebase_admin.initialize_app(firebase_cred)

tags_metadata = [
    {
        "name": "Proxy",
        "description": ". . .",
    },
]
