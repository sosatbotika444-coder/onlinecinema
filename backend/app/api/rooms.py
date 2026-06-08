from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import current_participant
from app.models import ChatMessage, Participant, Room, Video
from app.schemas import (
    ParticipantOut,
    PublicRoomOut,
    RoomCreate,
    RoomJoin,
    RoomJoinResponse,
    RoomOut,
    VideoLinkCreate,
    VideoOut,
)
from app.security import create_room_code, create_session_token, hash_password, verify_password
from app.serializers import serialize_room
from app.video_sources import resolve_video_url

router = APIRouter(prefix="/rooms", tags=["rooms"])


async def _unique_room_code(db: AsyncSession) -> str:
    for _ in range(20):
        code = create_room_code()
        exists = await db.scalar(select(Room.id).where(Room.code == code))
        if not exists:
            return code
    raise HTTPException(status_code=500, detail="Could not generate room code")


def _invite_link(code: str) -> str:
    settings = get_settings()
    return f"{settings.frontend_url.rstrip('/')}/room/{code}"


async def _system_message(db: AsyncSession, room_id: str, body: str) -> None:
    db.add(ChatMessage(room_id=room_id, participant_id=None, message_type="system", body=body))


@router.post("", response_model=RoomJoinResponse, status_code=status.HTTP_201_CREATED)
async def create_room(payload: RoomCreate, db: AsyncSession = Depends(get_db)) -> RoomJoinResponse:
    code = await _unique_room_code(db)
    room = Room(
        code=code,
        name=payload.name,
        max_participants=payload.max_participants,
        password_hash=hash_password(payload.password) if payload.password else None,
        is_private=payload.is_private,
        playback_updated_at=datetime.now(UTC),
    )
    db.add(room)
    await db.flush()

    owner = Participant(
        room_id=room.id,
        nickname=payload.nickname,
        avatar_url=payload.avatar_url,
        is_owner=True,
        is_online=True,
    )
    db.add(owner)
    await db.flush()
    room.owner_id = owner.id
    await _system_message(db, room.id, f"{owner.nickname} создал комнату")
    await db.commit()

    serialized = await serialize_room(db, room)
    return RoomJoinResponse(
        room=serialized,
        participant=ParticipantOut.model_validate(owner),
        token=create_session_token(owner.id, room.id, True),
        invite_link=_invite_link(room.code),
    )


@router.post("/{room_code}/join", response_model=RoomJoinResponse)
async def join_room(
    room_code: str,
    payload: RoomJoin,
    db: AsyncSession = Depends(get_db),
) -> RoomJoinResponse:
    room = await db.scalar(select(Room).where(Room.code == room_code.upper()))
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if not verify_password(payload.password, room.password_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wrong room password")

    online_count = await db.scalar(
        select(func.count(Participant.id)).where(Participant.room_id == room.id, Participant.is_online.is_(True))
    )
    if int(online_count or 0) >= room.max_participants:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room is full")

    participant = Participant(
        room_id=room.id,
        nickname=payload.nickname,
        avatar_url=payload.avatar_url,
        is_owner=False,
        is_online=True,
    )
    db.add(participant)
    await db.flush()
    await _system_message(db, room.id, f"{participant.nickname} присоединился")
    await db.commit()

    serialized = await serialize_room(db, room)
    return RoomJoinResponse(
        room=serialized,
        participant=ParticipantOut.model_validate(participant),
        token=create_session_token(participant.id, room.id, False),
        invite_link=_invite_link(room.code),
    )


@router.get("/public", response_model=list[PublicRoomOut])
async def public_rooms(db: AsyncSession = Depends(get_db)) -> list[PublicRoomOut]:
    rows = (
        await db.execute(
            select(Room, func.count(Participant.id))
            .outerjoin(
                Participant,
                (Participant.room_id == Room.id) & (Participant.is_online.is_(True)),
            )
            .where(Room.is_private.is_(False))
            .group_by(Room.id)
            .order_by(Room.created_at.desc())
            .limit(30)
        )
    ).all()
    return [
        PublicRoomOut(
            code=room.code,
            name=room.name,
            online_count=int(online_count or 0),
            max_participants=room.max_participants,
            has_video=bool(room.current_video_id),
            created_at=room.created_at,
        )
        for room, online_count in rows
    ]


@router.get("/{room_code}", response_model=RoomOut)
async def get_room(room_code: str, db: AsyncSession = Depends(get_db)) -> RoomOut:
    room = await db.scalar(select(Room).where(Room.code == room_code.upper()))
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return await serialize_room(db, room)


@router.post("/{room_code}/leave")
async def leave_room(
    room_code: str,
    participant: Participant = Depends(current_participant),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    room = await db.scalar(select(Room).where(Room.code == room_code.upper()))
    if not room or participant.room_id != room.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    participant.is_online = False
    participant.socket_id = None
    participant.last_seen = datetime.now(UTC)
    room.is_playing = False
    room.playback_updated_at = datetime.now(UTC)
    await _system_message(db, room.id, f"{participant.nickname} вышел")
    await db.commit()
    return {"status": "left"}


@router.post("/{room_code}/videos", response_model=VideoOut, status_code=status.HTTP_201_CREATED)
async def add_video_link(
    room_code: str,
    payload: VideoLinkCreate,
    participant: Participant = Depends(current_participant),
    db: AsyncSession = Depends(get_db),
) -> VideoOut:
    room = await db.scalar(select(Room).where(Room.code == room_code.upper()))
    if not room or participant.room_id != room.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if not participant.is_owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can change video")

    resolved = resolve_video_url(str(payload.url))
    video = Video(
        room_id=room.id,
        created_by_id=participant.id,
        source_type=resolved.source_type,
        url=resolved.url,
        embed_url=resolved.embed_url,
        title=payload.title or resolved.title,
    )
    db.add(video)
    await db.flush()
    room.current_video_id = video.id
    room.is_playing = False
    room.playback_position = 0
    room.playback_updated_at = datetime.now(UTC)
    await _system_message(db, room.id, "Видео обновлено")
    await db.commit()
    return VideoOut.model_validate(video)
