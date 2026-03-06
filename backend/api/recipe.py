"""레시피 추출 API.

POST /v1/recipe/extract — YouTube 영상에서 레시피 추출
POST /v1/recipe/parse-text — 외부 텍스트에서 레시피 구조화
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models.recipe import RecipeCore, RecipeCoreIngredient
from services.gemini_client import GeminiClient, GeminiError, GeminiRateLimited
from services.recipe_extract import get_or_extract_recipe
from services.recipe_transform import transform_recipe
from services.transcript import collect_transcript

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recipe", tags=["recipe"])


# ── Request 스키마 ──


class UserIngredientInput(BaseModel):
    name: str
    amount: float | None = None
    unit: str | None = None


class ExtractRequest(BaseModel):
    video_id: str = Field(..., min_length=1, max_length=20)
    servings: int = Field(default=2, ge=1, le=20)
    user_ingredients: list[UserIngredientInput] = Field(default_factory=list)


class ParseTextRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=10000)
    servings: int = Field(default=2, ge=1, le=20)
    user_ingredients: list[UserIngredientInput] = Field(default_factory=list)


# ── 엔드포인트 ──


@router.post("/extract")
async def extract_recipe(
    req: ExtractRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """YouTube 영상에서 레시피를 추출하고 인원수 변환 + GAP 분석."""
    # 1) 캐시 확인 (ingredients eager load)
    stmt = (
        select(RecipeCore)
        .options(selectinload(RecipeCore.ingredients))
        .where(
            RecipeCore.source_type == "youtube",
            RecipeCore.source_id == req.video_id,
        )
    )
    result = await session.execute(stmt)
    cached = result.scalar_one_or_none()

    if cached:
        logger.info("Cache hit for video %s", req.video_id)
        return _build_response(cached, cached.ingredients, req)

    # 2) 레시피 텍스트 수집
    transcript = await collect_transcript(session, req.video_id)

    if transcript.source == "flow_d":
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "EXTRACTION_FAILED",
                    "message": transcript.text,
                    "details": {"source": "flow_d", "video_id": req.video_id},
                }
            },
        )

    # 3) Gemini 추출 + DB 저장
    try:
        gemini = GeminiClient()
        recipe_core, _ = await get_or_extract_recipe(
            session, gemini, transcript.text, "youtube", req.video_id
        )
    except GeminiRateLimited as e:
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": str(e),
                    "details": {},
                }
            },
        ) from e
    except GeminiError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "EXTRACTION_FAILED",
                    "message": str(e),
                    "details": {"video_id": req.video_id},
                }
            },
        ) from e

    # ingredients를 다시 로드 (commit 후 relationship 접근 위해)
    stmt2 = (
        select(RecipeCore)
        .options(selectinload(RecipeCore.ingredients))
        .where(RecipeCore.id == recipe_core.id)
    )
    result2 = await session.execute(stmt2)
    recipe_core = result2.scalar_one()

    return _build_response(recipe_core, recipe_core.ingredients, req)


@router.post("/parse-text")
async def parse_text_recipe(
    req: ParseTextRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """외부 텍스트에서 레시피를 구조화하고 인원수 변환 + GAP 분석."""
    # source_id = 텍스트 해시 (동일 텍스트 중복 추출 방지)
    text_hash = hashlib.sha256(req.text.encode()).hexdigest()[:16]
    source_id = f"text_{text_hash}"

    # 캐시 확인
    stmt = (
        select(RecipeCore)
        .options(selectinload(RecipeCore.ingredients))
        .where(
            RecipeCore.source_type == "text",
            RecipeCore.source_id == source_id,
        )
    )
    result = await session.execute(stmt)
    cached = result.scalar_one_or_none()

    if cached:
        logger.info("Cache hit for text hash %s", text_hash)
        return _build_response(cached, cached.ingredients, req)

    # Gemini 추출
    try:
        gemini = GeminiClient()
        recipe_core, _ = await get_or_extract_recipe(
            session, gemini, req.text, "text", source_id
        )
    except GeminiRateLimited as e:
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": str(e),
                    "details": {},
                }
            },
        ) from e
    except GeminiError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "EXTRACTION_FAILED",
                    "message": str(e),
                    "details": {},
                }
            },
        ) from e

    # Reload with ingredients
    stmt2 = (
        select(RecipeCore)
        .options(selectinload(RecipeCore.ingredients))
        .where(RecipeCore.id == recipe_core.id)
    )
    result2 = await session.execute(stmt2)
    recipe_core = result2.scalar_one()

    return _build_response(recipe_core, recipe_core.ingredients, req)


def _build_response(
    recipe: RecipeCore,
    ingredients: list[RecipeCoreIngredient],
    req: ExtractRequest | ParseTextRequest,
) -> dict[str, Any]:
    """RecipeCore → API 응답 dict."""
    user_ings = [
        {"name": ui.name, "amount": ui.amount, "unit": ui.unit}
        for ui in req.user_ingredients
    ]

    transformed = transform_recipe(
        recipe=recipe,
        ingredients=ingredients,
        requested_servings=req.servings,
        user_ingredients=user_ings,
    )

    return {"recipe": transformed}
