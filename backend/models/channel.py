from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, UUIDPrimaryKey


class YoutubeChannel(UUIDPrimaryKey, Base):
    __tablename__ = "youtube_channels"

    channel_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    channel_name: Mapped[str] = mapped_column(String(200), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    subscriber_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    favorited_by: Mapped[list["UserFavoriteChannel"]] = relationship(  # noqa: F821
        back_populates="channel", cascade="all, delete-orphan"
    )
    videos: Mapped[list["ChannelVideoIndex"]] = relationship(  # noqa: F821
        back_populates="channel", cascade="all, delete-orphan"
    )
