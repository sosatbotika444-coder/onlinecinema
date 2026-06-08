from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import current_participant
from app.models import ChatMessage, Participant, Room, Video
from app.schemas import UploadCompleteRequest, UploadModeResponse, UploadPresignRequest, UploadPresignResponse, VideoOut
from app.storage import build_storage_key, create_presigned_upload, public_url_for_key, safe_filename
from app.video_sources import validate_upload

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.get("/mode", response_model=UploadModeResponse)
async def upload_mode() -> UploadModeResponse:
    settings = get_settings()
    return UploadModeResponse(
        mode="s3" if settings.s3_bucket else "local",
        max_size_bytes=settings.max_upload_size_bytes,
    )


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


@router.post("/direct", response_model=VideoOut)
async def direct_upload(
    room_code: str = Form(..., min_length=4, max_length=12),
    file: UploadFile = File(...),
    participant: Participant = Depends(current_participant),
    db: AsyncSession = Depends(get_db),
) -> VideoOut:
    settings = get_settings()
    room = await db.scalar(select(Room).where(Room.code == room_code.upper()))
    if not room or participant.room_id != room.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if not participant.is_owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can change video")

    filename = safe_filename(file.filename or "video")
    content_type = file.content_type or "application/octet-stream"
    validate_upload(filename, content_type, 1, settings.max_upload_size_bytes)
    size = 0
    upload_root = Path(settings.local_upload_dir)
    room_dir = upload_root / room.code
    room_dir.mkdir(parents=True, exist_ok=True)
    target = room_dir / f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{filename}"

    try:
        with target.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_size_bytes:
                    target.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File is too large",
                    )
                output.write(chunk)
    finally:
        await file.close()

    if size == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty")
    validate_upload(filename, content_type, size, settings.max_upload_size_bytes)

    media_path = target.as_posix()
    media_relative_path = media_path.removeprefix(upload_root.as_posix()).lstrip("/")
    url = f"{settings.api_public_url.rstrip('/')}/media/{media_relative_path}"
    video = Video(
        room_id=room.id,
        created_by_id=participant.id,
        source_type="upload",
        url=url,
        embed_url=None,
        title=filename,
        mime_type=content_type,
        storage_key=media_path,
        size_bytes=size,
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
