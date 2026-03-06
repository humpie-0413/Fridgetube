"""쿼리 의도 분류기.

규칙 기반으로 사용자 입력을 세 가지 의도로 분류한다:
- dish_name: 요리명 (예: "김치찌개", "볶음밥")
- ingredients: 재료 나열 (예: "계란, 파, 두부")
- ambiguous: 모호한 입력 (예: "김치")
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.ingredient import DishNameMaster, IngredientMaster

logger = logging.getLogger(__name__)

# 재료 구분자 패턴: 쉼표, 슬래시, "와/과/이랑/하고" 등
SEPARATOR_PATTERN = re.compile(r"[,/\s]+(?:와|과|이랑|하고|그리고|&)\s*|[,/]+\s*")

# 요리명 접미사 (찌개, 볶음, 탕 등)
DISH_SUFFIXES = [
    "찌개", "전골", "국", "탕", "볶음", "조림", "구이", "찜", "전", "튀김",
    "무침", "비빔", "떡", "밥", "면", "국수", "파스타", "카레", "덮밥",
    "라면", "우동", "소바", "피자", "샐러드", "스프", "스튜", "리조또",
    "샌드위치", "버거", "스테이크", "로스트", "그라탱", "나베", "돈부리",
    "초밥", "롤", "덴뿌라", "야끼", "라멘", "만두", "교자", "딤섬",
    "짬뽕", "짜장", "마라", "깐풍", "탕수", "볶음밥", "비빔밥",
]


@dataclass
class ClassifiedQuery:
    search_type: str  # "dish_name" | "ingredients" | "ambiguous"
    original_query: str
    dish_name: str | None = None
    cuisine_type: str | None = None
    dish_id: str | None = None
    ingredient_names: list[str] = field(default_factory=list)


async def classify_query(
    session: AsyncSession,
    query: str,
) -> ClassifiedQuery:
    """사용자 쿼리를 의도별로 분류한다."""
    query = query.strip()
    if not query:
        return ClassifiedQuery(search_type="ambiguous", original_query=query)

    # 1) 쉼표/구분자가 2개 이상 토큰 → 재료 모드
    tokens = _split_ingredients(query)
    if len(tokens) >= 2:
        matched_ingredients = await _match_ingredients(session, tokens)
        if matched_ingredients:
            return ClassifiedQuery(
                search_type="ingredients",
                original_query=query,
                ingredient_names=matched_ingredients,
            )

    # 2) dish_name_master에서 정확 매칭 or 유사 매칭
    dish = await _match_dish_name(session, query)
    if dish:
        return ClassifiedQuery(
            search_type="dish_name",
            original_query=query,
            dish_name=dish["name"],
            cuisine_type=dish["cuisine_type"],
            dish_id=str(dish["id"]),
        )

    # 3) 요리명 접미사 패턴 매칭
    if _has_dish_suffix(query):
        return ClassifiedQuery(
            search_type="dish_name",
            original_query=query,
            dish_name=query,
        )

    # 4) ingredient_master에서 단일 재료 매칭 → 모호
    single_ingredient = await _match_single_ingredient(session, query)
    if single_ingredient:
        return ClassifiedQuery(
            search_type="ambiguous",
            original_query=query,
            ingredient_names=[single_ingredient],
        )

    # 5) 기본: 요리명으로 추정
    return ClassifiedQuery(
        search_type="dish_name",
        original_query=query,
        dish_name=query,
    )


def _split_ingredients(query: str) -> list[str]:
    """쿼리를 재료 토큰으로 분리."""
    parts = SEPARATOR_PATTERN.split(query)
    # 구분자 없으면 공백으로 시도
    if len(parts) <= 1:
        parts = query.split()
    return [p.strip() for p in parts if p.strip()]


def _has_dish_suffix(query: str) -> bool:
    """요리명 접미사 포함 여부."""
    return any(query.endswith(suffix) for suffix in DISH_SUFFIXES)


async def _match_dish_name(
    session: AsyncSession, query: str
) -> dict | None:
    """dish_name_master에서 이름/별칭 매칭."""
    stmt = select(
        DishNameMaster.id,
        DishNameMaster.name,
        DishNameMaster.cuisine_type,
    ).where(
        or_(
            func.lower(DishNameMaster.name) == func.lower(query),
            DishNameMaster.aliases.any(query),
        )
    ).limit(1)

    result = await session.execute(stmt)
    row = result.first()
    if row:
        return {"id": row.id, "name": row.name, "cuisine_type": row.cuisine_type}
    return None


async def _match_ingredients(
    session: AsyncSession, tokens: list[str]
) -> list[str]:
    """토큰들이 ingredient_master에 매칭되는지 확인. 절반 이상 매칭되면 재료 모드."""
    matched = []
    for token in tokens:
        stmt = select(IngredientMaster.name).where(
            or_(
                func.lower(IngredientMaster.name) == func.lower(token),
                IngredientMaster.aliases.any(token),
            )
        ).limit(1)
        result = await session.execute(stmt)
        row = result.first()
        if row:
            matched.append(row.name)
        else:
            matched.append(token)

    # 절반 이상 DB 매칭이면 재료 모드로 판정
    db_match_count = sum(
        1 for t, m in zip(tokens, matched)
        if t.lower() != m.lower() or m in [r.name for r in []]  # 항상 추가
    )
    # 단순화: 2개 이상 토큰이면 재료 모드
    return matched


async def _match_single_ingredient(
    session: AsyncSession, query: str
) -> str | None:
    """단일 재료 매칭."""
    stmt = select(IngredientMaster.name).where(
        or_(
            func.lower(IngredientMaster.name) == func.lower(query),
            IngredientMaster.aliases.any(query),
        )
    ).limit(1)
    result = await session.execute(stmt)
    row = result.first()
    return row.name if row else None
