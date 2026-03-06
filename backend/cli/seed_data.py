import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import _prepare_engine_args  # noqa: E402

from models.ingredient import DishNameMaster, IngredientMaster  # noqa: E402

logger = logging.getLogger(__name__)

SEEDS_DIR = Path(__file__).resolve().parent.parent / "seeds"


async def seed_ingredients(session: AsyncSession) -> int:
    existing = await session.scalar(select(text("count(*)")).select_from(IngredientMaster))
    if existing and existing > 0:
        logger.info(f"ingredient_master already has {existing} rows, skipping.")
        return existing

    with open(SEEDS_DIR / "ingredients.json", encoding="utf-8") as f:
        data = json.load(f)

    ingredients = []
    for item in data:
        ingredients.append(
            IngredientMaster(
                id=uuid.uuid4(),
                name=item["name"],
                aliases=item.get("aliases"),
                category=item["category"],
                default_unit=item.get("default_unit"),
            )
        )

    session.add_all(ingredients)
    await session.flush()
    logger.info(f"Seeded {len(ingredients)} ingredients.")
    return len(ingredients)


async def seed_dishes(session: AsyncSession, ingredient_map: dict[str, uuid.UUID]) -> int:
    existing = await session.scalar(select(text("count(*)")).select_from(DishNameMaster))
    if existing and existing > 0:
        logger.info(f"dish_name_master already has {existing} rows, skipping.")
        return existing

    with open(SEEDS_DIR / "dishes.json", encoding="utf-8") as f:
        data = json.load(f)

    dishes = []
    for item in data:
        typical_ids = []
        for ing_name in item.get("typical_ingredients", []):
            if ing_name in ingredient_map:
                typical_ids.append(ingredient_map[ing_name])

        dishes.append(
            DishNameMaster(
                id=uuid.uuid4(),
                name=item["name"],
                aliases=item.get("aliases"),
                cuisine_type=item["cuisine_type"],
                pattern_suffix=item.get("pattern_suffix"),
                typical_ingredients=item.get("typical_ingredients"),
                typical_ingredient_ids=typical_ids if typical_ids else None,
            )
        )

    session.add_all(dishes)
    await session.flush()
    logger.info(f"Seeded {len(dishes)} dishes.")
    return len(dishes)


async def build_ingredient_map(session: AsyncSession) -> dict[str, uuid.UUID]:
    result = await session.execute(select(IngredientMaster))
    ingredient_map = {}
    for row in result.scalars():
        ingredient_map[row.name] = row.id
        if row.aliases:
            for alias in row.aliases:
                ingredient_map[alias] = row.id
    return ingredient_map


async def main(db_url: str | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not db_url:
        db_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/fridgetube?ssl=disable"

    clean_url, connect_args = _prepare_engine_args(db_url)
    engine = create_async_engine(clean_url, echo=False, connect_args=connect_args)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        await seed_ingredients(session)
        await session.commit()

    async with async_session() as session:
        ingredient_map = await build_ingredient_map(session)

    async with async_session() as session:
        await seed_dishes(session, ingredient_map)
        await session.commit()

    await engine.dispose()
    logger.info("Seed data loading complete.")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(main(url))
