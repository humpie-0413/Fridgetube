"""역방향 레시피 추론.

사용자가 가진 재료로 만들 수 있는 요리를 추천한다.
dish_name_master의 typical_ingredients를 기반으로 매칭 점수를 계산한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.ingredient import DishNameMaster

logger = logging.getLogger(__name__)


@dataclass
class DishCandidate:
    dish_id: str
    dish_name: str
    cuisine_type: str
    typical_ingredients: list[str]
    matched_ingredients: list[str]
    missing_ingredients: list[str]
    match_score: float  # 0.0 ~ 1.0


async def find_dishes_by_ingredients(
    session: AsyncSession,
    ingredient_names: list[str],
    top_k: int = 10,
) -> list[DishCandidate]:
    """재료 목록으로 만들 수 있는 후보 요리를 반환한다.

    매칭 점수 = (매칭된 재료 수) / (전체 typical_ingredients 수)
    """
    if not ingredient_names:
        return []

    normalized_names = [name.strip().lower() for name in ingredient_names]

    stmt = select(
        DishNameMaster.id,
        DishNameMaster.name,
        DishNameMaster.cuisine_type,
        DishNameMaster.typical_ingredients,
        DishNameMaster.popularity_score,
    ).where(
        DishNameMaster.typical_ingredients.isnot(None),
    )

    result = await session.execute(stmt)
    rows = result.all()

    candidates: list[DishCandidate] = []

    for row in rows:
        typical = row.typical_ingredients or []
        if not typical:
            continue

        typical_lower = [t.lower() for t in typical]
        matched = []
        missing = []

        for i, t in enumerate(typical_lower):
            found = any(
                user_ing in t or t in user_ing
                for user_ing in normalized_names
            )
            if found:
                matched.append(typical[i])
            else:
                missing.append(typical[i])

        if not matched:
            continue

        match_score = len(matched) / len(typical)
        # 인기도 가산 (최대 0.1)
        popularity_bonus = min((row.popularity_score or 0) / 100, 0.1)

        candidates.append(
            DishCandidate(
                dish_id=str(row.id),
                dish_name=row.name,
                cuisine_type=row.cuisine_type,
                typical_ingredients=typical,
                matched_ingredients=matched,
                missing_ingredients=missing,
                match_score=round(match_score + popularity_bonus, 3),
            )
        )

    candidates.sort(key=lambda c: c.match_score, reverse=True)
    return candidates[:top_k]
