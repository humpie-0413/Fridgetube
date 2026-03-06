"""로컬 검색 서비스.

channel_video_index에서 3단계 우선순위 검색을 수행한다.

검색 전략 (우선순위 순):
1. 정확 매칭 (ILIKE '%query%'): 제목에 검색어가 그대로 포함된 결과
2. tsvector plainto_tsquery 매칭: 토큰 기반 full-text 검색
3. pg_trgm similarity 매칭: 오타/유사어 퍼지 검색

정확 매칭 결과가 5개 이상이면 fuzzy(tsvector/trgm) 결과를 생략한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import Float, and_, func, literal, select, text, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from models.channel import YoutubeChannel
from models.video import ChannelVideoIndex

logger = logging.getLogger(__name__)

# pg_trgm 유사도 임계값
TRGM_THRESHOLD = 0.15

# 정확 매칭 결과가 이 수 이상이면 fuzzy 결과 생략
EXACT_CUTOFF = 5


@dataclass
class SearchResult:
    video_id: str
    title: str
    description_text: str | None
    has_recipe_in_desc: bool
    channel_name: str
    channel_id: str
    published_at: datetime | None
    score: float


async def search_videos(
    session: AsyncSession,
    query: str,
    limit: int = 20,
    channel_ids: list[str] | None = None,
) -> list[SearchResult]:
    """3단계 우선순위 검색 (정확 > tsvector > pg_trgm).

    Args:
        session: DB 세션
        query: 검색어 (예: "김치찌개", "김치찌게")
        limit: 최대 결과 수
        channel_ids: 필터할 youtube_channels.channel_id 목록 (None이면 전체)

    Returns:
        SearchResult 리스트 (score 내림차순)
    """
    now = datetime.now(timezone.utc)

    base_join = ChannelVideoIndex.channel_id == YoutubeChannel.id
    alive_condition = ChannelVideoIndex.expires_at >= now

    channel_filter = None
    if channel_ids:
        channel_filter = YoutubeChannel.channel_id.in_(channel_ids)

    select_columns = [
        ChannelVideoIndex.video_id,
        ChannelVideoIndex.title,
        ChannelVideoIndex.description_text,
        ChannelVideoIndex.has_recipe_in_desc,
        YoutubeChannel.channel_name,
        YoutubeChannel.channel_id.label("yt_channel_id"),
        ChannelVideoIndex.published_at,
    ]

    def _base_conditions() -> list:
        conds = [base_join, alive_condition]
        if channel_filter is not None:
            conds.append(channel_filter)
        return conds

    # === Tier 1: 정확 매칭 (ILIKE) — 검색어가 제목에 그대로 포함 ===
    pattern = f"%{query}%"
    exact_conditions = _base_conditions()
    exact_conditions.append(ChannelVideoIndex.title.ilike(pattern))

    # 제목이 검색어와 완전히 같거나 짧은 쪽에 높은 점수
    exact_score = (literal(100.0) + func.similarity(ChannelVideoIndex.title, query).cast(Float) * 10).label("score")

    exact_stmt = (
        select(*select_columns, exact_score)
        .join(YoutubeChannel, base_join)
        .where(and_(*exact_conditions))
    )

    exact_result = await session.execute(exact_stmt.order_by(text("score DESC")).limit(limit))
    exact_rows = exact_result.all()

    # 정확 매칭이 충분하면 fuzzy 생략
    if len(exact_rows) >= EXACT_CUTOFF:
        logger.info("Exact match cutoff: %d results for '%s'", len(exact_rows), query)
        return _rows_to_results(exact_rows)

    exact_video_ids = {row.video_id for row in exact_rows}

    # === Tier 2: tsvector 검색 ===
    ts_rank_title = func.ts_rank(ChannelVideoIndex.tsv_title, func.plainto_tsquery("simple", query))
    ts_rank_desc = func.ts_rank(ChannelVideoIndex.tsv_description, func.plainto_tsquery("simple", query))
    ts_score = (literal(50.0) + ts_rank_title * 3 + ts_rank_desc).label("score")

    ts_conditions = _base_conditions()
    ts_conditions.append(
        text(
            "channel_video_index.tsv_title @@ plainto_tsquery('simple', :q) "
            "OR channel_video_index.tsv_description @@ plainto_tsquery('simple', :q)"
        ).bindparams(q=query)
    )

    ts_stmt = (
        select(*select_columns, ts_score)
        .join(YoutubeChannel, base_join)
        .where(and_(*ts_conditions))
    )

    # === Tier 3: pg_trgm 유사도 검색 ===
    trgm_score = (func.similarity(ChannelVideoIndex.title, query).cast(Float) * 10).label("score")

    trgm_conditions = _base_conditions()
    trgm_conditions.append(
        text("similarity(channel_video_index.title, :q) > :threshold").bindparams(
            q=query, threshold=TRGM_THRESHOLD
        )
    )

    trgm_stmt = (
        select(*select_columns, trgm_score)
        .join(YoutubeChannel, base_join)
        .where(and_(*trgm_conditions))
    )

    # Tier 2 + 3 UNION ALL + 중복 제거
    combined = union_all(ts_stmt, trgm_stmt).subquery("combined")

    fuzzy_stmt = (
        select(
            combined.c.video_id,
            combined.c.title,
            combined.c.description_text,
            combined.c.has_recipe_in_desc,
            combined.c.channel_name,
            combined.c.yt_channel_id,
            combined.c.published_at,
            func.max(combined.c.score).label("max_score"),
        )
        .group_by(
            combined.c.video_id,
            combined.c.title,
            combined.c.description_text,
            combined.c.has_recipe_in_desc,
            combined.c.channel_name,
            combined.c.yt_channel_id,
            combined.c.published_at,
        )
        .order_by(text("max_score DESC"))
        .limit(limit)
    )

    fuzzy_result = await session.execute(fuzzy_stmt)
    fuzzy_rows = fuzzy_result.all()

    # 정확 매칭 결과를 상위에, fuzzy 결과를 하위에 합산 (중복 제거)
    results = _rows_to_results(exact_rows)
    for row in fuzzy_rows:
        if row.video_id not in exact_video_ids:
            results.append(_row_to_result(row, score_attr="max_score"))

    return results[:limit]


def _rows_to_results(rows: list) -> list[SearchResult]:
    return [
        SearchResult(
            video_id=row.video_id,
            title=row.title,
            description_text=row.description_text,
            has_recipe_in_desc=row.has_recipe_in_desc,
            channel_name=row.channel_name,
            channel_id=row.yt_channel_id,
            published_at=row.published_at,
            score=float(row.score) if row.score else 0.0,
        )
        for row in rows
    ]


def _row_to_result(row: object, score_attr: str = "score") -> SearchResult:
    return SearchResult(
        video_id=row.video_id,
        title=row.title,
        description_text=row.description_text,
        has_recipe_in_desc=row.has_recipe_in_desc,
        channel_name=row.channel_name,
        channel_id=row.yt_channel_id,
        published_at=row.published_at,
        score=float(getattr(row, score_attr, 0.0) or 0.0),
    )


async def search_videos_simple(
    session: AsyncSession,
    query: str,
    limit: int = 20,
) -> list[SearchResult]:
    """간단한 LIKE 기반 폴백 검색 (tsvector/trgm 사용 불가 시)."""
    now = datetime.now(timezone.utc)
    pattern = f"%{query}%"

    stmt = (
        select(
            ChannelVideoIndex.video_id,
            ChannelVideoIndex.title,
            ChannelVideoIndex.description_text,
            ChannelVideoIndex.has_recipe_in_desc,
            YoutubeChannel.channel_name,
            YoutubeChannel.channel_id.label("yt_channel_id"),
            ChannelVideoIndex.published_at,
        )
        .join(YoutubeChannel, ChannelVideoIndex.channel_id == YoutubeChannel.id)
        .where(
            and_(
                ChannelVideoIndex.expires_at >= now,
                ChannelVideoIndex.title.ilike(pattern),
            )
        )
        .order_by(ChannelVideoIndex.published_at.desc())
        .limit(limit)
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        SearchResult(
            video_id=row.video_id,
            title=row.title,
            description_text=row.description_text,
            has_recipe_in_desc=row.has_recipe_in_desc,
            channel_name=row.channel_name,
            channel_id=row.yt_channel_id,
            published_at=row.published_at,
            score=1.0,
        )
        for row in rows
    ]
