import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, UUIDPrimaryKey


class ChannelVideoIndex(UUIDPrimaryKey, Base):
    __tablename__ = "channel_video_index"
    __table_args__ = (
        {"comment": "YouTube API data - 30day TTL (expires_at)"},
    )

    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("youtube_channels.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    video_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_recipe_in_desc: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tsv_title: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    tsv_description: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    channel: Mapped["YoutubeChannel"] = relationship(back_populates="videos")  # noqa: F821


class YoutubeVideoSnapshot(UUIDPrimaryKey, Base):
    __tablename__ = "youtube_video_snapshot"
    __table_args__ = (
        {"comment": "YouTube API metadata - 30day TTL (expires_at)"},
    )

    video_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    yt_channel_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    channel_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    view_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    like_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
