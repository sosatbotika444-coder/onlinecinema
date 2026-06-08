from datetime import UTC, datetime
from typing import Any

import socketio
from fastapi import HTTPException
from sqlalchemy import select

from app.config import Settings
from app.database import AsyncSessionLocal
from app.models import ChatMessage, Participant, Room, Video
from app.rate_limit import SlidingWindowRateLimiter
from app.schemas import ChatMessageOut, PlaybackState, VideoOut
from app.security import decode_session_token
from app.serializers import recent_messages, serialize_room
from app.video_sources import resolve_video_url

chat_limiter = SlidingWindowRateLimiter(limit=8, window_seconds=10)


def create_socket_server(settings: Settings) -> socketio.AsyncServer:
    manager = None
    if settings.redis_url and not settings.is_test:
        manager = socketio.AsyncRedisManager(settings.redis_url, channel="sexparty")
    sio = socketio.AsyncServer(
        async_mode="asgi",
        cors_allowed_origins=settings.cors_origin_list or "*",
        client_manager=manager,
        ping_interval=20,
        ping_timeout=15,
    )
    register_handlers(sio)
    return sio


async def _emit_room_state(sio: socketio.AsyncServer, db, room: Room) -> None:
    state = (await serialize_room(db, room)).model_dump(mode="json")
    await sio.emit("room:state", state, room=room.code)


async def _emit_system(sio: socketio.AsyncServer, room: Room, body: str) -> None:
    payload = {
        "id": f"system-{datetime.now(UTC).timestamp()}",
        "participant_id": None,
        "nickname": None,
        "message_type": "system",
        "body": body,
        "created_at": datetime.now(UTC).isoformat(),
    }
    await sio.emit("system:notice", payload, room=room.code)
    await sio.emit("chat:message", payload, room=room.code)


def _playback_payload(room: Room) -> dict[str, Any]:
    return PlaybackState(
        is_playing=room.is_playing,
        position=room.playback_position,
        updated_at=room.playback_updated_at,
    ).model_dump(mode="json")


async def _session_participant(sio: socketio.AsyncServer, sid: str):
    session = await sio.get_session(sid)
    participant_id = session.get("participant_id")
    db = AsyncSessionLocal()
    participant = await db.get(Participant, participant_id)
    if not participant:
        await db.close()
        return None, None, None
    room = await db.get(Room, participant.room_id)
    if not room:
        await db.close()
        return None, None, None
    return db, participant, room


async def _owner_or_error(sio: socketio.AsyncServer, sid: str):
    db, participant, room = await _session_participant(sio, sid)
    if not participant or not room or not participant.is_owner:
        if db:
            await db.close()
        await sio.emit("error:notice", {"message": "Only room owner can control playback"}, to=sid)
        return None, None, None
    return db, participant, room


def register_handlers(sio: socketio.AsyncServer) -> None:
    @sio.event
    async def connect(sid: str, environ: dict, auth: dict | None) -> None:
        token = (auth or {}).get("token")
        if not token:
            raise ConnectionRefusedError("Missing session token")
        try:
            payload = decode_session_token(token)
        except HTTPException as exc:
            raise ConnectionRefusedError(exc.detail) from exc

        async with AsyncSessionLocal() as db:
            participant = await db.get(Participant, payload.get("sub"))
            if not participant:
                raise ConnectionRefusedError("Participant not found")
            room = await db.get(Room, participant.room_id)
            if not room:
                raise ConnectionRefusedError("Room not found")

            was_online = participant.is_online
            participant.is_online = True
            participant.socket_id = sid
            participant.last_seen = datetime.now(UTC)
            await db.commit()

            await sio.save_session(
                sid,
                {
                    "participant_id": participant.id,
                    "room_id": room.id,
                    "room_code": room.code,
                    "is_owner": participant.is_owner,
                },
            )
            await sio.enter_room(sid, room.code)
            await sio.emit("room:state", (await serialize_room(db, room)).model_dump(mode="json"), to=sid)
            await sio.emit(
                "chat:history",
                [message.model_dump(mode="json") for message in await recent_messages(db, room.id)],
                to=sid,
            )
            if not was_online:
                body = f"{participant.nickname} снова подключился"
                db.add(ChatMessage(room_id=room.id, participant_id=None, message_type="system", body=body))
                await db.commit()
                await _emit_system(sio, room, body)
            await _emit_room_state(sio, db, room)

    @sio.event
    async def disconnect(sid: str) -> None:
        try:
            session = await sio.get_session(sid)
        except KeyError:
            return
        async with AsyncSessionLocal() as db:
            participant = await db.get(Participant, session.get("participant_id"))
            if not participant:
                return
            room = await db.get(Room, participant.room_id)
            if not room:
                return

            participant.is_online = False
            participant.socket_id = None
            participant.last_seen = datetime.now(UTC)
            room.is_playing = False
            room.playback_updated_at = datetime.now(UTC)
            body = f"{participant.nickname} потерял соединение"
            db.add(ChatMessage(room_id=room.id, participant_id=None, message_type="system", body=body))
            await db.commit()

            await sio.emit(
                "participant:offline",
                {"participant_id": participant.id, "nickname": participant.nickname},
                room=room.code,
            )
            await sio.emit("playback:state", _playback_payload(room), room=room.code)
            await _emit_system(sio, room, body)
            await _emit_room_state(sio, db, room)

    @sio.on("presence:heartbeat")
    async def presence_heartbeat(sid: str, data: dict | None = None) -> None:
        session = await sio.get_session(sid)
        async with AsyncSessionLocal() as db:
            participant = await db.get(Participant, session.get("participant_id"))
            if participant:
                participant.last_seen = datetime.now(UTC)
                participant.is_online = True
                await db.commit()

    @sio.on("room:join")
    async def room_join(sid: str, data: dict | None = None) -> None:
        session = await sio.get_session(sid)
        async with AsyncSessionLocal() as db:
            room = await db.get(Room, session.get("room_id"))
            if room:
                await sio.enter_room(sid, room.code)
                await _emit_room_state(sio, db, room)

    @sio.on("room:leave")
    async def room_leave(sid: str, data: dict | None = None) -> None:
        await disconnect(sid)

    @sio.on("playback:play")
    async def playback_play(sid: str, data: dict | None = None) -> None:
        db, participant, room = await _owner_or_error(sio, sid)
        if not room:
            return
        position = float((data or {}).get("position", room.playback_position))
        room.is_playing = True
        room.playback_position = max(position, 0)
        room.playback_updated_at = datetime.now(UTC)
        db.add(ChatMessage(room_id=room.id, participant_id=None, message_type="system", body="Видео запущено"))
        await db.commit()
        await sio.emit("playback:state", _playback_payload(room), room=room.code)
        await _emit_system(sio, room, "Видео запущено")
        await db.close()

    @sio.on("playback:pause")
    async def playback_pause(sid: str, data: dict | None = None) -> None:
        db, participant, room = await _owner_or_error(sio, sid)
        if not room:
            return
        position = float((data or {}).get("position", room.playback_position))
        room.is_playing = False
        room.playback_position = max(position, 0)
        room.playback_updated_at = datetime.now(UTC)
        db.add(
            ChatMessage(room_id=room.id, participant_id=None, message_type="system", body="Видео поставлено на паузу")
        )
        await db.commit()
        await sio.emit("playback:state", _playback_payload(room), room=room.code)
        await _emit_system(sio, room, "Видео поставлено на паузу")
        await db.close()

    @sio.on("playback:seek")
    async def playback_seek(sid: str, data: dict | None = None) -> None:
        db, participant, room = await _owner_or_error(sio, sid)
        if not room:
            return
        room.playback_position = max(float((data or {}).get("position", 0)), 0)
        room.playback_updated_at = datetime.now(UTC)
        await db.commit()
        await sio.emit("playback:state", _playback_payload(room), room=room.code)
        await db.close()

    @sio.on("playback:volume")
    async def playback_volume(sid: str, data: dict | None = None) -> None:
        db, participant, room = await _owner_or_error(sio, sid)
        if not room:
            return
        await sio.emit(
            "playback:volume",
            {"volume": max(0, min(float((data or {}).get("volume", 1)), 1))},
            room=room.code,
            skip_sid=sid,
        )
        await db.close()

    @sio.on("video:change")
    async def video_change(sid: str, data: dict | None = None) -> None:
        db, participant, room = await _owner_or_error(sio, sid)
        if not room:
            return
        data = data or {}
        video = None
        if data.get("video_id"):
            video = await db.get(Video, data["video_id"])
        elif data.get("url"):
            resolved = resolve_video_url(str(data["url"]))
            video = Video(
                room_id=room.id,
                created_by_id=participant.id,
                source_type=resolved.source_type,
                url=resolved.url,
                embed_url=resolved.embed_url,
                title=data.get("title") or resolved.title,
            )
            db.add(video)
            await db.flush()
        if not video or video.room_id != room.id:
            await sio.emit("error:notice", {"message": "Video not found"}, to=sid)
            await db.close()
            return
        room.current_video_id = video.id
        room.is_playing = False
        room.playback_position = 0
        room.playback_updated_at = datetime.now(UTC)
        db.add(ChatMessage(room_id=room.id, participant_id=None, message_type="system", body="Видео обновлено"))
        await db.commit()
        await sio.emit("video:change", VideoOut.model_validate(video).model_dump(mode="json"), room=room.code)
        await _emit_system(sio, room, "Видео обновлено")
        await _emit_room_state(sio, db, room)
        await db.close()

    @sio.on("chat:message")
    async def chat_message(sid: str, data: dict | None = None) -> None:
        session = await sio.get_session(sid)
        body = str((data or {}).get("body", "")).strip()
        if not body:
            return
        if len(body) > 500:
            body = body[:500]
        key = f"{session.get('room_id')}:{session.get('participant_id')}"
        if not chat_limiter.allow(key):
            await sio.emit("error:notice", {"message": "Слишком много сообщений. Подождите пару секунд."}, to=sid)
            return
        async with AsyncSessionLocal() as db:
            participant = await db.get(Participant, session.get("participant_id"))
            room = await db.get(Room, session.get("room_id"))
            if not participant or not room:
                return
            message = ChatMessage(room_id=room.id, participant_id=participant.id, message_type="user", body=body)
            db.add(message)
            await db.flush()
            payload = ChatMessageOut(
                id=message.id,
                participant_id=participant.id,
                nickname=participant.nickname,
                message_type="user",
                body=message.body,
                created_at=message.created_at,
            ).model_dump(mode="json")
            await db.commit()
            await sio.emit("chat:message", payload, room=room.code)

    @sio.on("chat:typing")
    async def chat_typing(sid: str, data: dict | None = None) -> None:
        session = await sio.get_session(sid)
        async with AsyncSessionLocal() as db:
            participant = await db.get(Participant, session.get("participant_id"))
            room = await db.get(Room, session.get("room_id"))
            if participant and room:
                await sio.emit(
                    "chat:typing",
                    {"participant_id": participant.id, "nickname": participant.nickname, "typing": bool((data or {}).get("typing", True))},
                    room=room.code,
                    skip_sid=sid,
                )
