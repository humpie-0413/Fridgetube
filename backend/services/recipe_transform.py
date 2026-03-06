"""scaling_strategy 기반 분량 조절 + GAP 분석 서비스.

레시피 원본(base_servings) → 요청 인원수(requested_servings) 변환.
각 재료의 scaling_strategy에 따라 다른 변환 로직 적용.
GAP은 런타임 계산 (DB에 저장하지 않음).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from models.recipe import RecipeCore, RecipeCoreIngredient
from services.ingredient_gap import BASIC_SEASONINGS

# GAP 상태 상수
GAP_SUFFICIENT = "SUFFICIENT"
GAP_PARTIAL = "PARTIAL"
GAP_UNKNOWN_QTY = "UNKNOWN_QTY"
GAP_MISSING = "MISSING"
GAP_BASIC_ASSUMED = "BASIC_ASSUMED"

# verdict 메시지
_VERDICTS = {
    (0.9, 1.01): "모든 재료가 준비되었습니다!",
    (0.7, 0.9): "거의 준비 완료!",
    (0.4, 0.7): "몇 가지 재료를 더 준비하세요.",
    (0.0, 0.4): "장보기가 필요합니다.",
}


@dataclass
class ScaledIngredient:
    name: str
    original_amount: float | None
    scaled_amount: float | None
    unit: str | None
    scaling_strategy: str
    is_optional: bool
    gap_status: str = GAP_MISSING
    gap_detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class GapSummary:
    total: int = 0
    sufficient: int = 0
    partial: int = 0
    missing: int = 0
    unknown_qty: int = 0
    basic_assumed: int = 0
    gap_score: float = 0.0
    verdict: str = ""
    shopping_list: list[dict[str, str]] = field(default_factory=list)


def scale_amount(
    amount: float | None,
    strategy: str,
    ratio: float,
) -> float | None:
    """scaling_strategy에 따라 amount를 변환한다.

    Args:
        amount: 원본 양
        strategy: linear | stepwise | to_taste | fixed
        ratio: requested_servings / base_servings

    Returns:
        변환된 양 (None이면 수치 없음)
    """
    if amount is None:
        return None

    if strategy == "linear":
        return round(amount * ratio, 2)

    if strategy == "stepwise":
        scaled = amount * ratio
        return float(round(scaled))  # 정수 반올림

    if strategy in ("to_taste", "fixed"):
        return amount  # 원본 유지

    # 알 수 없는 전략 → linear fallback
    return round(amount * ratio, 2)


def transform_recipe(
    recipe: RecipeCore,
    ingredients: list[RecipeCoreIngredient],
    requested_servings: int,
    user_ingredients: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """레시피를 요청 인원수에 맞게 변환하고 GAP을 분석한다.

    Args:
        recipe: RecipeCore 모델
        ingredients: RecipeCoreIngredient 리스트
        requested_servings: 요청 인원수
        user_ingredients: [{"name": "계란", "amount": 6, "unit": "개"}, ...]

    Returns:
        API 응답용 dict
    """
    base = recipe.base_servings or 2
    ratio = requested_servings / base

    user_map = _build_user_map(user_ingredients or [])

    scaled_ingredients: list[ScaledIngredient] = []
    for ing in sorted(ingredients, key=lambda x: x.sort_order or 0):
        scaled_amt = scale_amount(ing.amount, ing.scaling_strategy, ratio)
        si = ScaledIngredient(
            name=ing.name,
            original_amount=ing.amount,
            scaled_amount=scaled_amt,
            unit=ing.unit,
            scaling_strategy=ing.scaling_strategy,
            is_optional=ing.is_optional,
        )
        _compute_gap_status(si, user_map)
        scaled_ingredients.append(si)

    gap_summary = _compute_gap_summary(scaled_ingredients)

    return {
        "dish_name": recipe.dish_name,
        "base_servings": base,
        "base_servings_source": recipe.base_servings_source or "default",
        "requested_servings": requested_servings,
        "confidence_score": recipe.confidence_score,
        "prompt_version": recipe.prompt_version,
        "ingredients": [
            {
                "name": si.name,
                "amount": si.scaled_amount,
                "unit": si.unit,
                "scaling_strategy": si.scaling_strategy,
                "is_optional": si.is_optional,
                "gap_status": si.gap_status,
                "gap_detail": si.gap_detail,
            }
            for si in scaled_ingredients
        ],
        "steps": recipe.steps,
        "cooking_time_min": recipe.cooking_time_min,
        "difficulty": recipe.difficulty,
        "ingredient_gap_summary": {
            "total": gap_summary.total,
            "sufficient": gap_summary.sufficient,
            "partial": gap_summary.partial,
            "missing": gap_summary.missing,
            "unknown_qty": gap_summary.unknown_qty,
            "basic_assumed": gap_summary.basic_assumed,
            "gap_score": gap_summary.gap_score,
            "verdict": gap_summary.verdict,
            "shopping_list": gap_summary.shopping_list,
        },
    }


def _build_user_map(
    user_ingredients: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """사용자 재료를 {이름(소문자): {amount, unit}} 맵으로 변환."""
    result: dict[str, dict[str, Any]] = {}
    for ing in user_ingredients:
        name = ing.get("name", "").strip().lower()
        if name:
            result[name] = {
                "amount": ing.get("amount"),
                "unit": ing.get("unit"),
            }
    return result


def _find_user_ingredient(
    name: str,
    user_map: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """재료 이름으로 사용자 보유 재료를 찾는다 (부분 매칭)."""
    name_lower = name.strip().lower()

    # 정확 매칭
    if name_lower in user_map:
        return user_map[name_lower]

    # 부분 매칭
    for user_name, data in user_map.items():
        if user_name in name_lower or name_lower in user_name:
            return data

    return None


def _compute_gap_status(
    si: ScaledIngredient,
    user_map: dict[str, dict[str, Any]],
) -> None:
    """개별 재료의 GAP 상태를 계산."""
    # 기본 양념 체크
    if si.name in BASIC_SEASONINGS:
        si.gap_status = GAP_BASIC_ASSUMED
        si.gap_detail = {"reason": "기본 양념으로 가정"}
        return

    user_ing = _find_user_ingredient(si.name, user_map)

    if user_ing is None:
        si.gap_status = GAP_MISSING
        si.gap_detail = {"user_has": None, "recipe_needs": si.scaled_amount, "shortage": None}
        return

    user_amount = user_ing.get("amount")
    recipe_needs = si.scaled_amount

    # 수량 정보 없는 경우
    if user_amount is None or recipe_needs is None:
        si.gap_status = GAP_UNKNOWN_QTY
        si.gap_detail = {"user_has": user_amount, "recipe_needs": recipe_needs, "shortage": None}
        return

    # 충분/부족 판단
    shortage = max(recipe_needs - user_amount, 0)
    if shortage <= 0:
        si.gap_status = GAP_SUFFICIENT
    else:
        si.gap_status = GAP_PARTIAL

    si.gap_detail = {
        "user_has": user_amount,
        "recipe_needs": recipe_needs,
        "shortage": round(shortage, 2),
    }


def _compute_gap_summary(ingredients: list[ScaledIngredient]) -> GapSummary:
    """전체 GAP 요약을 계산."""
    summary = GapSummary()
    countable = 0  # gap_score 계산에 포함할 재료 수

    for si in ingredients:
        if si.is_optional:
            continue

        summary.total += 1

        if si.gap_status == GAP_SUFFICIENT:
            summary.sufficient += 1
            countable += 1
        elif si.gap_status == GAP_PARTIAL:
            summary.partial += 1
            countable += 1
        elif si.gap_status == GAP_UNKNOWN_QTY:
            summary.unknown_qty += 1
            countable += 1
        elif si.gap_status == GAP_BASIC_ASSUMED:
            summary.basic_assumed += 1
        elif si.gap_status == GAP_MISSING:
            summary.missing += 1
            countable += 1
            # 쇼핑 리스트에 추가
            amount_str = ""
            if si.scaled_amount is not None:
                amount_str = f"{si.scaled_amount}"
                if si.unit:
                    amount_str += si.unit
            summary.shopping_list.append({"name": si.name, "amount": amount_str})

    # PARTIAL도 쇼핑 리스트에 추가 (부족분만)
    for si in ingredients:
        if si.gap_status == GAP_PARTIAL and not si.is_optional:
            shortage = si.gap_detail.get("shortage", 0)
            if shortage and shortage > 0:
                amount_str = f"{shortage}"
                if si.unit:
                    amount_str += si.unit
                summary.shopping_list.append({"name": si.name, "amount": amount_str})

    # gap_score 계산
    if countable > 0:
        good = summary.sufficient + summary.unknown_qty
        summary.gap_score = round(good / countable, 2)
    else:
        summary.gap_score = 1.0

    # verdict
    for (lo, hi), msg in _VERDICTS.items():
        if lo <= summary.gap_score < hi:
            summary.verdict = msg
            break
    else:
        summary.verdict = "장보기가 필요합니다."

    return summary
