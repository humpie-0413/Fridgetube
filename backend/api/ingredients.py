"""재료 API.

GET  /v1/ingredients/search?q={query} — 재료명 자동완성
POST /v1/ingredients/recognize        — 사진 재료 인식 (Gemini Vision)
"""

from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.ingredient import IngredientMaster
from services.gemini_client import GeminiError, GeminiRateLimited
from services.vision import recognize_ingredients

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingredients", tags=["ingredients"])


class IngredientItem(BaseModel):
    id: str
    name: str
    category: str


class IngredientsSearchResponse(BaseModel):
    ingredients: list[IngredientItem]


@router.get("/search", response_model=IngredientsSearchResponse)
async def search_ingredients(
    q: str = Query(..., min_length=1, max_length=50, description="검색어"),
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_db),
) -> IngredientsSearchResponse:
    """재료 자동완성 검색.

    이름 prefix 매칭 + aliases 배열 매칭 + pg_trgm 유사도를 결합한다.
    """
    pattern = f"{q}%"

    # prefix 매칭 (이름 시작)
    prefix_stmt = (
        select(
            IngredientMaster.id,
            IngredientMaster.name,
            IngredientMaster.category,
        )
        .where(
            or_(
                IngredientMaster.name.ilike(pattern),
                IngredientMaster.aliases.any(q),
            )
        )
        .order_by(IngredientMaster.name)
        .limit(limit)
    )

    result = await session.execute(prefix_stmt)
    rows = result.all()

    # prefix 매칭 결과가 부족하면 contains 매칭 추가
    if len(rows) < limit:
        contains_pattern = f"%{q}%"
        existing_ids = {row.id for row in rows}

        contains_stmt = (
            select(
                IngredientMaster.id,
                IngredientMaster.name,
                IngredientMaster.category,
            )
            .where(
                IngredientMaster.name.ilike(contains_pattern),
                IngredientMaster.id.notin_(existing_ids) if existing_ids else True,
            )
            .order_by(IngredientMaster.name)
            .limit(limit - len(rows))
        )

        result2 = await session.execute(contains_stmt)
        rows = list(rows) + list(result2.all())

    return IngredientsSearchResponse(
        ingredients=[
            IngredientItem(
                id=str(row.id),
                name=row.name,
                category=row.category,
            )
            for row in rows
        ]
    )


# ── 사진 인식 ──

MAX_IMAGE_SIZE = 4 * 1024 * 1024  # 4MB


class RecognizedIngredient(BaseModel):
    name: str
    estimated_amount: float | None = None
    unit: str | None = None
    confidence: float
    alternatives: list[str] = Field(default_factory=list)


class RecognizeRequest(BaseModel):
    image: str = Field(
        ...,
        description="data:image/jpeg;base64,... 또는 순수 base64 문자열",
    )


class RecognizeResponse(BaseModel):
    ingredients: list[RecognizedIngredient]


@router.post("/recognize", response_model=RecognizeResponse)
async def recognize_ingredients_endpoint(
    req: RecognizeRequest,
) -> RecognizeResponse:
    """사진에서 식재료를 인식한다 (Gemini Vision)."""
    # data URI prefix 제거
    raw = req.image
    if raw.startswith("data:"):
        # data:image/jpeg;base64,/9j/4AAQ...
        parts = raw.split(",", 1)
        if len(parts) != 2:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "INVALID_IMAGE", "message": "잘못된 이미지 형식", "details": {}}},
            )
        raw = parts[1]

    # base64 디코딩
    try:
        image_bytes = base64.b64decode(raw)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_BASE64", "message": "base64 디코딩 실패", "details": {}}},
        )

    # 크기 검증
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "IMAGE_TOO_LARGE",
                    "message": f"이미지 크기가 {MAX_IMAGE_SIZE // (1024*1024)}MB를 초과합니다",
                    "details": {"size": len(image_bytes), "max": MAX_IMAGE_SIZE},
                }
            },
        )

    # Gemini Vision 호출
    try:
        results = await recognize_ingredients(image_bytes)
    except GeminiRateLimited as e:
        raise HTTPException(
            status_code=429,
            detail={"error": {"code": "RATE_LIMITED", "message": str(e), "details": {}}},
        ) from e
    except GeminiError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "RECOGNITION_FAILED", "message": str(e), "details": {}}},
        ) from e

    return RecognizeResponse(
        ingredients=[RecognizedIngredient(**r) for r in results]
    )
