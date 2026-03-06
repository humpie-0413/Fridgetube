"""통합 스마트 검색 API.

POST /v1/search/videos — 쿼리를 분류하고 로컬 우선 검색 + YouTube fallback을 수행한다.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.ingredient_gap import estimate_gap
from services.local_search import SearchResult, search_videos
from services.query_classifier import ClassifiedQuery, classify_query
from services.reverse_recipe import DishCandidate, find_dishes_by_ingredients

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


# ── Request / Response 스키마 ──


class UserIngredientInput(BaseModel):
    name: str
    amount: float | None = None
    unit: str | None = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    user_ingredients: list[UserIngredientInput] = Field(default_factory=list)
    servings: int = Field(default=2, ge=1, le=20)
    mode: str = Field(default="video", pattern=r"^(video|recipe)$")
    channel_filter: bool = False
    sort_by: str = Field(default="relevance", pattern=r"^(relevance|view_count|least_missing)$")
    limit: int = Field(default=10, ge=1, le=50)
    cursor: str | None = None


class ChannelInfo(BaseModel):
    id: str
    name: str


class GapEstimateResponse(BaseModel):
    source: str
    is_estimate: bool
    estimated_missing: int
    gap_score: float


class VideoResult(BaseModel):
    video_id: str
    title: str
    channel: ChannelInfo
    thumbnail: str
    view_count: int | None = None
    duration_seconds: int | None = None
    has_cached_recipe: bool = False
    ingredient_gap_estimate: GapEstimateResponse | None = None


class DetectedQueryInfo(BaseModel):
    dish_name: str | None = None
    cuisine_type: str | None = None
    ingredient_names: list[str] = Field(default_factory=list)
    dish_candidates: list[dict[str, Any]] | None = None


class SearchResponse(BaseModel):
    search_type: str
    detected_query: DetectedQueryInfo
    videos: list[VideoResult]
    next_cursor: str | None = None
    total_estimate: int


# ── 엔드포인트 ──


@router.post("/videos", response_model=SearchResponse)
async def search_videos_endpoint(
    req: SearchRequest,
    session: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """통합 스마트 검색."""
    # 1) 쿼리 분류
    classified = await classify_query(session, req.query)
    logger.info("Query classified: %s -> %s", req.query, classified.search_type)

    user_ing_names = [ing.name for ing in req.user_ingredients]

    # 2) 검색 실행
    if classified.search_type == "ingredients":
        return await _search_by_ingredients(
            session, classified, user_ing_names, req
        )
    else:
        return await _search_by_dish_name(
            session, classified, user_ing_names, req
        )


async def _search_by_dish_name(
    session: AsyncSession,
    classified: ClassifiedQuery,
    user_ing_names: list[str],
    req: SearchRequest,
) -> SearchResponse:
    """요리명/모호 검색: 로컬 tsvector+trgm 검색."""
    search_query = classified.dish_name or classified.original_query

    # 로컬 검색
    results = await search_videos(
        session,
        query=search_query,
        limit=req.limit,
    )

    # typical_ingredients로 GAP 추정
    typical = await _get_typical_ingredients(session, search_query)

    videos = _build_video_results(results, typical, user_ing_names)

    # sort
    if req.sort_by == "least_missing":
        videos.sort(
            key=lambda v: v.ingredient_gap_estimate.estimated_missing
            if v.ingredient_gap_estimate else 999
        )

    return SearchResponse(
        search_type=classified.search_type,
        detected_query=DetectedQueryInfo(
            dish_name=classified.dish_name,
            cuisine_type=classified.cuisine_type,
        ),
        videos=videos,
        total_estimate=len(videos),
    )


async def _search_by_ingredients(
    session: AsyncSession,
    classified: ClassifiedQuery,
    user_ing_names: list[str],
    req: SearchRequest,
) -> SearchResponse:
    """재료 기반 검색: 역방향 추론 → 후보 요리별 로컬 검색."""
    # 역방향 추론
    candidates = await find_dishes_by_ingredients(
        session, classified.ingredient_names, top_k=5
    )

    all_videos: list[VideoResult] = []
    seen_video_ids: set[str] = set()

    # 후보 요리 각각에 대해 로컬 검색
    for candidate in candidates:
        results = await search_videos(
            session,
            query=candidate.dish_name,
            limit=max(req.limit // len(candidates), 3) if candidates else req.limit,
        )
        gap = estimate_gap(candidate.typical_ingredients, user_ing_names or classified.ingredient_names)

        for r in results:
            if r.video_id in seen_video_ids:
                continue
            seen_video_ids.add(r.video_id)

            all_videos.append(
                VideoResult(
                    video_id=r.video_id,
                    title=r.title,
                    channel=ChannelInfo(id=r.channel_id, name=r.channel_name),
                    thumbnail=f"https://i.ytimg.com/vi/{r.video_id}/mqdefault.jpg",
                    has_cached_recipe=r.has_recipe_in_desc,
                    ingredient_gap_estimate=GapEstimateResponse(
                        source="typical_ingredients",
                        is_estimate=True,
                        estimated_missing=gap.estimated_missing,
                        gap_score=gap.gap_score,
                    ),
                )
            )

    # sort
    if req.sort_by == "least_missing":
        all_videos.sort(
            key=lambda v: v.ingredient_gap_estimate.estimated_missing
            if v.ingredient_gap_estimate else 999
        )

    dish_candidates_info = [
        {
            "dish_name": c.dish_name,
            "cuisine_type": c.cuisine_type,
            "match_score": c.match_score,
            "matched": c.matched_ingredients,
            "missing": c.missing_ingredients,
        }
        for c in candidates
    ]

    return SearchResponse(
        search_type="ingredients",
        detected_query=DetectedQueryInfo(
            ingredient_names=classified.ingredient_names,
            dish_candidates=dish_candidates_info,
        ),
        videos=all_videos[:req.limit],
        total_estimate=len(all_videos),
    )


def _build_video_results(
    results: list[SearchResult],
    typical_ingredients: list[str],
    user_ing_names: list[str],
) -> list[VideoResult]:
    """SearchResult → VideoResult 변환 + GAP 추정."""
    gap = None
    if typical_ingredients:
        gap = estimate_gap(typical_ingredients, user_ing_names)

    videos = []
    for r in results:
        gap_response = None
        if gap:
            gap_response = GapEstimateResponse(
                source="typical_ingredients",
                is_estimate=True,
                estimated_missing=gap.estimated_missing,
                gap_score=gap.gap_score,
            )

        videos.append(
            VideoResult(
                video_id=r.video_id,
                title=r.title,
                channel=ChannelInfo(id=r.channel_id, name=r.channel_name),
                thumbnail=f"https://i.ytimg.com/vi/{r.video_id}/mqdefault.jpg",
                has_cached_recipe=r.has_recipe_in_desc,
                ingredient_gap_estimate=gap_response,
            )
        )
    return videos


async def _get_typical_ingredients(
    session: AsyncSession, dish_name: str
) -> list[str]:
    """요리명에 해당하는 typical_ingredients를 조회."""
    from sqlalchemy import func, or_, select

    from models.ingredient import DishNameMaster

    stmt = select(DishNameMaster.typical_ingredients).where(
        or_(
            func.lower(DishNameMaster.name) == func.lower(dish_name),
            DishNameMaster.aliases.any(dish_name),
        )
    ).limit(1)

    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return row or []
