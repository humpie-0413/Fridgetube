"""Gemini 기반 레시피 추출 서비스.

텍스트(설명란/댓글/사용자 입력)를 Gemini에 전달하여 구조화된 레시피 JSON을 추출한다.
추출 결과는 recipe_core + recipe_core_ingredients에 캐싱 (source_type + source_id UNIQUE).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.recipe import RecipeCore, RecipeCoreIngredient
from services.gemini_client import GeminiClient, GeminiError

logger = logging.getLogger(__name__)

PROMPT_VERSION = "v1.0"

EXTRACT_PROMPT = """당신은 요리 레시피 전문 분석가입니다.
아래 텍스트에서 레시피 정보를 추출하여 JSON으로 반환하세요.

## 규칙
1. 텍스트에 레시피가 없으면 confidence_score를 0.1 이하로 설정
2. base_servings_source:
   - "explicit": 텍스트에 "N인분"이 명시된 경우
   - "inferred": 재료 양으로 추론한 경우
   - "default": 판단 불가 시 기본 2인분
3. scaling_strategy:
   - "linear": 비례 조절 (고기, 채소, 국물 등)
   - "stepwise": 정수로만 조절 (계란, 두부 등 개수 단위)
   - "to_taste": 맛보며 조절 (소금, 후추 등)
   - "fixed": 인원수 무관 고정 (식용유 적당량 등)
4. amount가 "약간", "적당량" 등 수치가 아니면 amount는 null, unit에 원문 그대로 기록
5. steps는 순서대로 배열

## 출력 JSON 스키마
{
  "dish_name": "요리 이름",
  "base_servings": 2,
  "base_servings_source": "explicit|inferred|default",
  "ingredients": [
    {
      "name": "재료 이름",
      "amount": 1.0,
      "unit": "개",
      "scaling_strategy": "linear|stepwise|to_taste|fixed",
      "is_optional": false
    }
  ],
  "steps": [
    {"order": 1, "text": "조리 단계 설명", "time_seconds": null}
  ],
  "cooking_time_min": 30,
  "difficulty": "easy|medium|hard",
  "confidence_score": 0.85
}

## 분석할 텍스트
{text}"""


async def extract_recipe_from_text(
    gemini: GeminiClient,
    text: str,
) -> dict[str, Any]:
    """텍스트에서 Gemini를 사용하여 레시피를 추출한다.

    Returns:
        추출된 레시피 dict (EXTRACT_PROMPT의 JSON 스키마에 맞춤)
    """
    prompt = EXTRACT_PROMPT.replace("{text}", text)
    result = await gemini.generate_json(prompt)
    result["prompt_version"] = PROMPT_VERSION
    return result


async def get_or_extract_recipe(
    session: AsyncSession,
    gemini: GeminiClient,
    text: str,
    source_type: str,
    source_id: str,
) -> tuple[RecipeCore, bool]:
    """캐시 확인 후 없으면 추출하여 DB에 저장한다.

    Args:
        session: DB 세션
        gemini: GeminiClient
        text: 레시피 텍스트
        source_type: "youtube" 또는 "text"
        source_id: video_id 또는 텍스트 해시

    Returns:
        (RecipeCore, cache_hit) 튜플
    """
    # ── 캐시 확인 ──
    stmt = select(RecipeCore).where(
        RecipeCore.source_type == source_type,
        RecipeCore.source_id == source_id,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        logger.info("Recipe cache hit: %s/%s", source_type, source_id)
        return existing, True

    # ── Gemini 추출 ──
    logger.info("Extracting recipe via Gemini for %s/%s", source_type, source_id)
    extracted = await extract_recipe_from_text(gemini, text)

    # ── DB 저장 ──
    recipe_core = _build_recipe_core(extracted, source_type, source_id, text)
    session.add(recipe_core)

    ingredients = _build_ingredients(extracted, recipe_core.id)
    session.add_all(ingredients)

    await session.commit()
    await session.refresh(recipe_core)

    logger.info("Recipe saved: %s (id=%s)", recipe_core.dish_name, recipe_core.id)
    return recipe_core, False


def _build_recipe_core(
    extracted: dict[str, Any],
    source_type: str,
    source_id: str,
    raw_text: str,
) -> RecipeCore:
    """추출 결과 → RecipeCore 모델 인스턴스."""
    steps = extracted.get("steps", [])
    if isinstance(steps, list):
        steps_json = steps
    else:
        steps_json = [{"order": 1, "text": str(steps)}]

    return RecipeCore(
        id=uuid.uuid4(),
        source_type=source_type,
        source_id=source_id,
        dish_name=extracted.get("dish_name", "알 수 없는 요리"),
        base_servings=extracted.get("base_servings", 2),
        base_servings_source=extracted.get("base_servings_source", "default"),
        steps=steps_json,
        cooking_time_min=extracted.get("cooking_time_min"),
        difficulty=extracted.get("difficulty"),
        raw_transcript=raw_text[:5000] if raw_text else None,
        confidence_score=extracted.get("confidence_score"),
        prompt_version=extracted.get("prompt_version", PROMPT_VERSION),
    )


def _build_ingredients(
    extracted: dict[str, Any],
    recipe_id: uuid.UUID,
) -> list[RecipeCoreIngredient]:
    """추출 결과 → RecipeCoreIngredient 리스트."""
    ingredients_data = extracted.get("ingredients", [])
    models: list[RecipeCoreIngredient] = []

    for i, ing in enumerate(ingredients_data):
        name = ing.get("name", "")
        if not name:
            continue

        amount = ing.get("amount")
        if amount is not None:
            try:
                amount = float(amount)
            except (ValueError, TypeError):
                amount = None

        models.append(
            RecipeCoreIngredient(
                id=uuid.uuid4(),
                recipe_id=recipe_id,
                raw_name=name,
                name=name,
                amount=amount,
                unit=ing.get("unit"),
                scaling_strategy=ing.get("scaling_strategy", "linear"),
                is_optional=ing.get("is_optional", False),
                sort_order=i,
            )
        )

    return models
