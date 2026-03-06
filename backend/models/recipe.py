import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, UUIDPrimaryKey


class RecipeCore(UUIDPrimaryKey, Base):
    __tablename__ = "recipe_core"
    __table_args__ = (
        UniqueConstraint("source_type", "source_id", name="uq_recipe_core_source"),
    )

    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    dish_name: Mapped[str] = mapped_column(String(200), nullable=False)
    base_servings: Mapped[int] = mapped_column(Integer, nullable=False)
    base_servings_source: Mapped[str] = mapped_column(String(20), default="default")
    steps: Mapped[dict] = mapped_column(JSONB, nullable=False)
    cooking_time_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(10), nullable=True)
    raw_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ingredients: Mapped[list["RecipeCoreIngredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan"
    )
    saved_by: Mapped[list["SavedRecipe"]] = relationship(  # noqa: F821
        back_populates="recipe", cascade="all, delete-orphan"
    )


class RecipeCoreIngredient(UUIDPrimaryKey, Base):
    __tablename__ = "recipe_core_ingredients"

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipe_core.id", ondelete="CASCADE"), nullable=False
    )
    ingredient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingredient_master.id", ondelete="SET NULL"), nullable=True
    )
    raw_name: Mapped[str] = mapped_column(String(200), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    scaling_strategy: Mapped[str] = mapped_column(String(20), default="linear")
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True)

    recipe: Mapped["RecipeCore"] = relationship(back_populates="ingredients")
