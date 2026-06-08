from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


def uuid_str() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    code: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    max_participants: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    current_video_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    playback_position: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    is_playing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    playback_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    participants: Mapped[list["Participant"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
    videos: Mapped[list["Video"]] = relationship(back_populates="room", cascade="all, delete-orphan")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    nickname: Mapped[str] = mapped_column(String(40), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(600), nullable=True)
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_online: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    socket_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    room: Mapped[Room] = relationship(back_populates="participants")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="participant")


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    created_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL"), nullable=True
    )
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    embed_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    title: Mapped[str | None] = mapped_column(String(180), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    room: Mapped[Room] = relationship(back_populates="videos")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    participant_id: Mapped[str | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL"), nullable=True
    )
    message_type: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    body: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    room: Mapped[Room] = relationship(back_populates="messages")
    participant: Mapped[Participant | None] = relationship(back_populates="messages")


class RoomEvent(Base):
    __tablename__ = "room_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
