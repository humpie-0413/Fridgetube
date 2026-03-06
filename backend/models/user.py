import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDPrimaryKey


class User(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="anonymous")
    provider_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    default_servings: Mapped[int] = mapped_column(Integer, default=2)

    favorite_channels: Mapped[list["UserFavoriteChannel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    ingredients: Mapped[list["UserIngredient"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    search_histories: Mapped[list["SearchHistory"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    saved_recipes: Mapped[list["SavedRecipe"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )


class UserFavoriteChannel(UUIDPrimaryKey, Base):
    __tablename__ = "user_favorite_channels"
    __table_args__ = (UniqueConstraint("user_id", "channel_id", name="uq_user_channel"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("youtube_channels.id", ondelete="CASCADE"), nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="favorite_channels")
    channel: Mapped["YoutubeChannel"] = relationship(back_populates="favorited_by")  # noqa: F821
