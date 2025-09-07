from fastapi import FastAPI
from core.configs import configs, tags_metadata
import logging
from utils import load_routers
from core.logging_setup import setup_logging
from infrastructure.redis import init_redis, close_redis
from contextlib import asynccontextmanager

setup_logging()

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_redis()
    yield
    # Shutdown
    await close_redis()

app = FastAPI(
    title=configs.PROJECT_NAME,
    version="0.0.1",
    docs_url=configs.DOCS_URL,
    openapi_tags=tags_metadata,
    openapi_url=f"{configs.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)
routes = ["http/health","http/get_screens_from_url", "http/manifest.json", "http/manifest.webmanifest", "http/retarget", "http/[...slug]"]
for router in load_routers(routes):
    app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    if configs.DEBUG:
        uvicorn.run("main:app", port=8000, reload=True)
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=8000)