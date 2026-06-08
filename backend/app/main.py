import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import health, rooms, uploads, videos
from app.config import get_settings
from app.database import engine
from app.models import Base
from app.sockets import create_socket_server

settings = get_settings()
Path(settings.local_upload_dir).mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("sexparty.startup")


async def initialize_database_with_retries() -> None:
    for attempt in range(1, 8):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database schema is ready")
            return
        except Exception:
            delay = min(2 * attempt, 20)
            logger.exception("Database schema initialization failed, retrying in %s seconds", delay)
            await asyncio.sleep(delay)
    logger.error("Database schema initialization failed after all retries")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_task: asyncio.Task | None = None
    if settings.auto_create_tables:
        db_task = asyncio.create_task(initialize_database_with_retries())
    try:
        yield
    finally:
        if db_task and not db_task.done():
            db_task.cancel()


fastapi_app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
fastapi_app.include_router(health.router, prefix="/api")
fastapi_app.include_router(rooms.router, prefix="/api")
fastapi_app.include_router(videos.router, prefix="/api")
fastapi_app.include_router(uploads.router, prefix="/api")
fastapi_app.mount("/media", StaticFiles(directory=settings.local_upload_dir), name="media")


@fastapi_app.get("/")
async def root_status() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@fastapi_app.get("/health")
async def root_health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}

sio = create_socket_server(settings)
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app, socketio_path="socket.io")
