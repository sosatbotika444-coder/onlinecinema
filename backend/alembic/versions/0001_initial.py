"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rooms",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=12), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("max_participants", sa.Integer(), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=True),
        sa.Column("is_private", sa.Boolean(), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=True),
        sa.Column("current_video_id", sa.String(length=36), nullable=True),
        sa.Column("playback_position", sa.Float(), nullable=False),
        sa.Column("is_playing", sa.Boolean(), nullable=False),
        sa.Column("playback_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_rooms_is_private", "rooms", ["is_private"])
    op.create_table(
        "participants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("room_id", sa.String(length=36), nullable=False),
        sa.Column("nickname", sa.String(length=40), nullable=False),
        sa.Column("avatar_url", sa.String(length=600), nullable=True),
        sa.Column("is_owner", sa.Boolean(), nullable=False),
        sa.Column("is_online", sa.Boolean(), nullable=False),
        sa.Column("socket_id", sa.String(length=128), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_participants_room_id", "participants", ["room_id"])
    op.create_table(
        "videos",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("room_id", sa.String(length=36), nullable=False),
        sa.Column("created_by_id", sa.String(length=36), nullable=True),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("url", sa.String(length=2000), nullable=False),
        sa.Column("embed_url", sa.String(length=2000), nullable=True),
        sa.Column("title", sa.String(length=180), nullable=True),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("storage_key", sa.String(length=1000), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["participants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_videos_room_id", "videos", ["room_id"])
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("room_id", sa.String(length=36), nullable=False),
        sa.Column("participant_id", sa.String(length=36), nullable=True),
        sa.Column("message_type", sa.String(length=20), nullable=False),
        sa.Column("body", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_room_id", "chat_messages", ["room_id"])
    op.create_table(
        "room_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("room_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_room_events_room_id", "room_events", ["room_id"])


def downgrade() -> None:
    op.drop_index("ix_room_events_room_id", table_name="room_events")
    op.drop_table("room_events")
    op.drop_index("ix_chat_messages_room_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_videos_room_id", table_name="videos")
    op.drop_table("videos")
    op.drop_index("ix_participants_room_id", table_name="participants")
    op.drop_table("participants")
    op.drop_index("ix_rooms_is_private", table_name="rooms")
    op.drop_table("rooms")
