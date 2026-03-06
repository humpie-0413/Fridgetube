from sqlalchemy import Float, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, UUIDPrimaryKey


class IngredientMaster(UUIDPrimaryKey, Base):
    __tablename__ = "ingredient_master"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    aliases: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    default_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    icon_url: Mapped[str | None] = mapped_column(Text, nullable=True)


class DishNameMaster(UUIDPrimaryKey, Base):
    __tablename__ = "dish_name_master"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    aliases: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    cuisine_type: Mapped[str] = mapped_column(String(20), nullable=False)
    pattern_suffix: Mapped[str | None] = mapped_column(String(20), nullable=True)
    typical_ingredients: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    typical_ingredient_ids: Mapped[list | None] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)
    popularity_score: Mapped[float] = mapped_column(Float, default=0)
