from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

SourceType = Literal["youtube", "vk", "rutube", "direct", "upload"]


class ParticipantCreate(BaseModel):
    nickname: str = Field(min_length=2, max_length=40)
    avatar_url: str | None = Field(default=None, max_length=600)


class RoomCreate(ParticipantCreate):
    name: str = Field(min_length=2, max_length=120)
    max_participants: int = Field(default=4, ge=2, le=4)
    password: str | None = Field(default=None, min_length=4, max_length=80)
    is_private: bool = True


class RoomJoin(ParticipantCreate):
    password: str | None = Field(default=None, max_length=80)


class ParticipantOut(BaseModel):
    id: str
    nickname: str
    avatar_url: str | None
    is_owner: bool
    is_online: bool
    last_seen: datetime

    model_config = {"from_attributes": True}


class VideoOut(BaseModel):
    id: str
    source_type: SourceType
    url: str
    embed_url: str | None
    title: str | None
    mime_type: str | None
    size_bytes: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageOut(BaseModel):
    id: str
    participant_id: str | None
    nickname: str | None = None
    message_type: Literal["user", "system"]
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PlaybackState(BaseModel):
    is_playing: bool
    position: float
    updated_at: datetime | None = None


class RoomOut(BaseModel):
    id: str
    code: str
    name: str
    max_participants: int
    is_private: bool
    owner_id: str | None
    current_video: VideoOut | None = None
    participants: list[ParticipantOut] = []
    playback: PlaybackState
    created_at: datetime


class RoomJoinResponse(BaseModel):
    room: RoomOut
    participant: ParticipantOut
    token: str
    invite_link: str


class PublicRoomOut(BaseModel):
    code: str
    name: str
    online_count: int
    max_participants: int
    has_video: bool
    created_at: datetime


class VideoResolveRequest(BaseModel):
    url: HttpUrl


class VideoLinkCreate(BaseModel):
    url: HttpUrl
    title: str | None = Field(default=None, max_length=180)


class VideoResolveResponse(BaseModel):
    source_type: SourceType
    url: str
    embed_url: str | None = None
    title: str | None = None
    playable_in_html5: bool


class UploadPresignRequest(BaseModel):
    room_code: str = Field(min_length=4, max_length=12)
    filename: str = Field(min_length=1, max_length=240)
    content_type: str = Field(min_length=3, max_length=120)
    size_bytes: int = Field(gt=0)


class UploadPresignResponse(BaseModel):
    upload_url: str
    fields: dict[str, str]
    method: Literal["POST"] = "POST"
    storage_key: str
    public_url: str | None
    max_size_bytes: int


class UploadCompleteRequest(BaseModel):
    room_code: str = Field(min_length=4, max_length=12)
    storage_key: str = Field(min_length=3, max_length=1000)
    filename: str = Field(min_length=1, max_length=240)
    content_type: str = Field(min_length=3, max_length=120)
    size_bytes: int = Field(gt=0)
    public_url: str | None = None


class HealthOut(BaseModel):
    status: Literal["ok"]
    app: str
    environment: str
