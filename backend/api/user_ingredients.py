"""보유 재료 CRUD API.

GET    /v1/user/ingredients            목록 조회
POST   /v1/user/ingredients            추가
PUT    /v1/user/ingredients/{id}       수정
DELETE /v1/user/ingredients/{id}       삭제
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.session_user import get_or_create_user
from database import get_db
from models.history import UserIngredient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/user/ingredients", tags=["user-ingredients"])


# ── 스키마 ──


class UserIngredientItem(BaseModel):
    id: str
    name: str
    amount: float | None = None
    unit: str | None = None
    source: str


class UserIngredientsResponse(BaseModel):
    ingredients: list[UserIngredientItem]


class AddIngredientRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    amount: float | None = None
    unit: str | None = Field(None, max_length=20)


class UpdateIngredientRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    amount: float | None = None
    unit: str | None = Field(None, max_length=20)


# ── 엔드포인트 ──


@router.get("", response_model=UserIngredientsResponse)
async def list_user_ingredients(
    session: AsyncSession = Depends(get_db),
    x_session_id: str | None = Header(None),
) -> UserIngredientsResponse:
    """보유 재료 목록 조회."""
    user = await get_or_create_user(session, x_session_id)

    stmt = (
        select(UserIngredient)
        .where(UserIngredient.user_id == user.id)
        .order_by(UserIngredient.created_at.desc())
    )
    result = await session.execute(stmt)
    ingredients = result.scalars().all()

    return UserIngredientsResponse(
        ingredients=[
            UserIngredientItem(
                id=str(ing.id),
                name=ing.name,
                amount=ing.amount,
                unit=ing.unit,
                source=ing.source,
            )
            for ing in ingredients
        ]
    )


@router.post("", response_model=UserIngredientItem, status_code=201)
async def add_user_ingredient(
    req: AddIngredientRequest,
    session: AsyncSession = Depends(get_db),
    x_session_id: str | None = Header(None),
) -> UserIngredientItem:
    """보유 재료 추가."""
    user = await get_or_create_user(session, x_session_id)

    ingredient = UserIngredient(
        user_id=user.id,
        name=req.name,
        amount=req.amount,
        unit=req.unit,
        source="manual",
    )
    session.add(ingredient)
    await session.commit()

    return UserIngredientItem(
        id=str(ingredient.id),
        name=ingredient.name,
        amount=ingredient.amount,
        unit=ingredient.unit,
        source=ingredient.source,
    )


@router.put("/{ingredient_id}", response_model=UserIngredientItem)
async def update_user_ingredient(
    ingredient_id: str,
    req: UpdateIngredientRequest,
    session: AsyncSession = Depends(get_db),
    x_session_id: str | None = Header(None),
) -> UserIngredientItem:
    """보유 재료 수정."""
    user = await get_or_create_user(session, x_session_id)

    try:
        uid = uuid.UUID(ingredient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": {"code": "INVALID_ID", "message": "유효하지 않은 ID", "details": {}}})

    stmt = select(UserIngredient).where(
        UserIngredient.id == uid,
        UserIngredient.user_id == user.id,
    )
    result = await session.execute(stmt)
    ingredient = result.scalar_one_or_none()

    if not ingredient:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "재료를 찾을 수 없습니다", "details": {}}},
        )

    if req.name is not None:
        ingredient.name = req.name
    if req.amount is not None:
        ingredient.amount = req.amount
    if req.unit is not None:
        ingredient.unit = req.unit

    await session.commit()

    return UserIngredientItem(
        id=str(ingredient.id),
        name=ingredient.name,
        amount=ingredient.amount,
        unit=ingredient.unit,
        source=ingredient.source,
    )


@router.delete("/{ingredient_id}")
async def delete_user_ingredient(
    ingredient_id: str,
    session: AsyncSession = Depends(get_db),
    x_session_id: str | None = Header(None),
) -> dict:
    """보유 재료 삭제."""
    user = await get_or_create_user(session, x_session_id)

    try:
        uid = uuid.UUID(ingredient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": {"code": "INVALID_ID", "message": "유효하지 않은 ID", "details": {}}})

    stmt = select(UserIngredient).where(
        UserIngredient.id == uid,
        UserIngredient.user_id == user.id,
    )
    result = await session.execute(stmt)
    ingredient = result.scalar_one_or_none()

    if not ingredient:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "재료를 찾을 수 없습니다", "details": {}}},
        )

    await session.delete(ingredient)
    await session.commit()

    return {"deleted": True, "id": ingredient_id}
