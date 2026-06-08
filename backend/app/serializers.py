from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMessage, Participant, Room, Video
from app.schemas import ChatMessageOut, ParticipantOut, PlaybackState, RoomOut, VideoOut


async def serialize_room(db: AsyncSession, room: Room) -> RoomOut:
    participants = (
        await db.execute(
            select(Participant).where(Participant.room_id == room.id).order_by(Participant.created_at.asc())
        )
    ).scalars().all()
    current_video = None
    if room.current_video_id:
        current_video = await db.get(Video, room.current_video_id)

    return RoomOut(
        id=room.id,
        code=room.code,
        name=room.name,
        max_participants=room.max_participants,
        is_private=room.is_private,
        owner_id=room.owner_id,
        current_video=VideoOut.model_validate(current_video) if current_video else None,
        participants=[ParticipantOut.model_validate(participant) for participant in participants],
        playback=PlaybackState(
            is_playing=room.is_playing,
            position=room.playback_position,
            updated_at=room.playback_updated_at,
        ),
        created_at=room.created_at,
    )


async def recent_messages(db: AsyncSession, room_id: str, limit: int = 80) -> list[ChatMessageOut]:
    rows = (
        await db.execute(
            select(ChatMessage, Participant.nickname)
            .outerjoin(Participant, Participant.id == ChatMessage.participant_id)
            .where(ChatMessage.room_id == room_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
    ).all()
    messages = [
        ChatMessageOut(
            id=message.id,
            participant_id=message.participant_id,
            nickname=nickname,
            message_type=message.message_type,
            body=message.body,
            created_at=message.created_at,
        )
        for message, nickname in rows
    ]
    return list(reversed(messages))
