from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import current_participant
from app.models import ChatMessage, Participant, Room, Video
from app.schemas import UploadCompleteRequest, UploadPresignRequest, UploadPresignResponse, VideoOut
from app.storage import build_storage_key, create_presigned_upload, public_url_for_key
from app.video_sources import validate_upload

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/presign", response_model=UploadPresignResponse)
async def presign_upload(
    payload: UploadPresignRequest,
    participant: Participant = Depends(current_participant),
    db: AsyncSession = Depends(get_db),
) -> UploadPresignResponse:
    settings = get_settings()
    room = await db.scalar(select(Room).where(Room.code == payload.room_code.upper()))
    if not room or participant.room_id != room.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    validate_upload(
        payload.filename,
        payload.content_type,
        payload.size_bytes,
        settings.max_upload_size_bytes,
    )
    key = build_storage_key(room.code, payload.filename)
    presigned = create_presigned_upload(settings, key, payload.content_type, payload.size_bytes)
    return UploadPresignResponse(
        upload_url=presigned["url"],
        fields=presigned["fields"],
        storage_key=key,
        public_url=public_url_for_key(settings, key),
        max_size_bytes=settings.max_upload_size_bytes,
    )


@router.post("/complete", response_model=VideoOut)
async def complete_upload(
    payload: UploadCompleteRequest,
    participant: Participant = Depends(current_participant),
    db: AsyncSession = Depends(get_db),
) -> VideoOut:
    settings = get_settings()
    room = await db.scalar(select(Room).where(Room.code == payload.room_code.upper()))
    if not room or participant.room_id != room.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if not participant.is_owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can change video")
    validate_upload(
        payload.filename,
        payload.content_type,
        payload.size_bytes,
        settings.max_upload_size_bytes,
    )
    url = payload.public_url or public_url_for_key(settings, payload.storage_key)
    if not url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Public file URL is not configured")

    video = Video(
        room_id=room.id,
        created_by_id=participant.id,
        source_type="upload",
        url=url,
        embed_url=None,
        title=payload.filename,
        mime_type=payload.content_type,
        storage_key=payload.storage_key,
        size_bytes=payload.size_bytes,
    )
    db.add(video)
    await db.flush()
    room.current_video_id = video.id
    room.is_playing = False
    room.playback_position = 0
    room.playback_updated_at = datetime.now(UTC)
    db.add(ChatMessage(room_id=room.id, participant_id=None, message_type="system", body="Видео загружено"))
    await db.commit()
    return VideoOut.model_validate(video)
