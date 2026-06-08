from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, rooms, uploads, videos
from app.config import get_settings
from app.database import engine
from app.models import Base
from app.sockets import create_socket_server

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_tables:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


fastapi_app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
fastapi_app.include_router(health.router, prefix="/api")
fastapi_app.include_router(rooms.router, prefix="/api")
fastapi_app.include_router(videos.router, prefix="/api")
fastapi_app.include_router(uploads.router, prefix="/api")

sio = create_socket_server(settings)
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app, socketio_path="socket.io")
