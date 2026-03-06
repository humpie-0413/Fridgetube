"""재료 GAP 추정 서비스.

검색 단계에서 typical_ingredients 기반으로 예상 GAP을 계산한다.
실제 레시피 추출 전이므로 "추정(estimate)" 결과이며,
정확한 GAP은 레시피 추출 후 recipe_transform에서 계산한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 기본 양념 목록 (대부분의 가정에 있다고 가정)
BASIC_SEASONINGS = {
    "소금", "설탕", "간장", "식용유", "참기름", "후추", "고춧가루",
    "된장", "고추장", "식초", "마늘", "생강", "깨", "참깨",
    "들기름", "미림", "맛술", "올리고당", "물엿", "굴소스",
    "케첩", "마요네즈", "버터", "올리브유",
}


@dataclass
class GapEstimate:
    source: str = "typical_ingredients"
    is_estimate: bool = True
    total_typical: int = 0
    user_has: int = 0
    estimated_missing: int = 0
    basic_assumed: int = 0
    gap_score: float = 1.0  # 0.0(전부 없음) ~ 1.0(전부 보유)
    missing_items: list[str] = field(default_factory=list)
    matched_items: list[str] = field(default_factory=list)


def estimate_gap(
    typical_ingredients: list[str],
    user_ingredient_names: list[str],
) -> GapEstimate:
    """typical_ingredients와 사용자 보유 재료를 비교하여 GAP을 추정한다.

    Args:
        typical_ingredients: 요리의 대표 재료 목록
        user_ingredient_names: 사용자가 보유한 재료 이름 목록

    Returns:
        GapEstimate 객체
    """
    if not typical_ingredients:
        return GapEstimate()

    user_set = {name.strip().lower() for name in user_ingredient_names}
    total = len(typical_ingredients)
    matched = []
    missing = []
    basic_count = 0

    for ingredient in typical_ingredients:
        ing_lower = ingredient.strip().lower()

        # 사용자 보유 재료와 매칭 (부분 문자열 매칭)
        if _is_matched(ing_lower, user_set):
            matched.append(ingredient)
        elif ingredient in BASIC_SEASONINGS:
            basic_count += 1
        else:
            missing.append(ingredient)

    user_has = len(matched)
    estimated_missing = len(missing)
    effective_total = total - basic_count

    if effective_total > 0:
        gap_score = round((user_has) / effective_total, 2)
    else:
        gap_score = 1.0

    return GapEstimate(
        total_typical=total,
        user_has=user_has,
        estimated_missing=estimated_missing,
        basic_assumed=basic_count,
        gap_score=gap_score,
        missing_items=missing,
        matched_items=matched,
    )


def _is_matched(ingredient: str, user_set: set[str]) -> bool:
    """재료 이름이 사용자 보유 재료와 매칭되는지 확인."""
    if ingredient in user_set:
        return True
    for user_ing in user_set:
        if user_ing in ingredient or ingredient in user_ing:
            return True
    return False
