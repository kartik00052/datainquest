from contextlib import asynccontextmanager

from fastapi import FastAPI

from daginquest.api import actions, health, incidents, metrics, webhooks
from daginquest.config import get_settings
from daginquest.db import session


@asynccontextmanager
async def lifespan(app: FastAPI):
    await session.init_pool(get_settings().database_url)
    yield
    await session.close_pool()


app = FastAPI(title="DagInquest", version="0.1.0", lifespan=lifespan)

for module in (health, webhooks, incidents, actions, metrics):
    app.include_router(module.router)
