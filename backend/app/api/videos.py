from fastapi import APIRouter

from app.schemas import VideoResolveRequest, VideoResolveResponse
from app.video_sources import resolve_video_url

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("/resolve", response_model=VideoResolveResponse)
async def resolve_video(payload: VideoResolveRequest) -> VideoResolveResponse:
    resolved = resolve_video_url(str(payload.url))
    return VideoResolveResponse(
        source_type=resolved.source_type,
        url=resolved.url,
        embed_url=resolved.embed_url,
        title=resolved.title,
        playable_in_html5=resolved.playable_in_html5,
    )
