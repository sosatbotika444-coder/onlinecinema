from fastapi import APIRouter

from app.config import get_settings
from app.schemas import HealthOut

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthOut)
async def health() -> HealthOut:
    settings = get_settings()
    return HealthOut(status="ok", app=settings.app_name, environment=settings.environment)
