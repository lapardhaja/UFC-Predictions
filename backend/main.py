from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

from backend.config import get_settings
from backend.database import Base, engine
from backend.routers import admin, events, fighters, fights, health, model as model_router

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    FastAPICache.init(InMemoryBackend(), prefix="ufc-cache")
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="UFC Predictor API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, tags=["health"])
    app.include_router(events.router, prefix="/api/v1")
    app.include_router(fights.router, prefix="/api/v1")
    app.include_router(fighters.router, prefix="/api/v1")
    app.include_router(model_router.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    return app


app = create_app()
