"""로컬 검색 서비스.

channel_video_index에서 tsvector(full-text) + pg_trgm(fuzzy) 검색을 수행한다.
한국어는 형태소 분석이 없으므로 'simple' 사전 + pg_trgm 유사도를 결합한다.

검색 전략:
1. tsvector plainto_tsquery 매칭 (정확한 단어 매칭)
2. pg_trgm similarity 매칭 (오타/유사어 매칭)
3. 두 결과를 합산하여 랭킹
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import Float, String, and_, cast, func, literal_column, select, text, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from models.channel import YoutubeChannel
from models.video import ChannelVideoIndex

logger = logging.getLogger(__name__)

# pg_trgm 유사도 임계값 (0.0 ~ 1.0)
# 한국어 제목은 긴 문자열에서 짧은 쿼리 매칭 시 유사도가 낮으므로 임계값을 낮게 설정
TRGM_THRESHOLD = 0.08


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
    """tsvector + pg_trgm 결합 검색.

    Args:
        session: DB 세션
        query: 검색어 (예: "김치찌개", "김치찌게")
        limit: 최대 결과 수
        channel_ids: 필터할 youtube_channels.channel_id 목록 (None이면 전체)

    Returns:
        SearchResult 리스트 (score 내림차순)
    """
    now = datetime.now(timezone.utc)

    # 기본 조인 조건
    base_join = ChannelVideoIndex.channel_id == YoutubeChannel.id
    alive_condition = ChannelVideoIndex.expires_at >= now

    # 채널 필터
    channel_filter = None
    if channel_ids:
        channel_filter = YoutubeChannel.channel_id.in_(channel_ids)

    # === 1) tsvector 검색 (정확한 매칭) ===
    ts_query = func.plainto_tsquery("simple", query)

    ts_rank_title = func.ts_rank(ChannelVideoIndex.tsv_title, ts_query)
    ts_rank_desc = func.ts_rank(ChannelVideoIndex.tsv_description, ts_query)
    # 제목 매칭에 가중치 3배
    ts_score = (ts_rank_title * 3 + ts_rank_desc).label("score")

    ts_conditions = [
        base_join,
        alive_condition,
        text(
            "channel_video_index.tsv_title @@ plainto_tsquery('simple', :q) "
            "OR channel_video_index.tsv_description @@ plainto_tsquery('simple', :q)"
        ).bindparams(q=query),
    ]
    if channel_filter is not None:
        ts_conditions.append(channel_filter)

    ts_stmt = (
        select(
            ChannelVideoIndex.video_id,
            ChannelVideoIndex.title,
            ChannelVideoIndex.description_text,
            ChannelVideoIndex.has_recipe_in_desc,
            YoutubeChannel.channel_name,
            YoutubeChannel.channel_id.label("yt_channel_id"),
            ChannelVideoIndex.published_at,
            ts_score,
        )
        .join(YoutubeChannel, base_join)
        .where(and_(*ts_conditions))
    )

    # === 2) pg_trgm 유사도 검색 (오타/유사어) ===
    trgm_title = func.similarity(ChannelVideoIndex.title, query)
    trgm_score = (trgm_title * 2).cast(Float).label("score")

    trgm_conditions = [
        base_join,
        alive_condition,
        text(
            "similarity(channel_video_index.title, :q) > :threshold"
        ).bindparams(q=query, threshold=TRGM_THRESHOLD),
    ]
    if channel_filter is not None:
        trgm_conditions.append(channel_filter)

    trgm_stmt = (
        select(
            ChannelVideoIndex.video_id,
            ChannelVideoIndex.title,
            ChannelVideoIndex.description_text,
            ChannelVideoIndex.has_recipe_in_desc,
            YoutubeChannel.channel_name,
            YoutubeChannel.channel_id.label("yt_channel_id"),
            ChannelVideoIndex.published_at,
            trgm_score,
        )
        .join(YoutubeChannel, base_join)
        .where(and_(*trgm_conditions))
    )

    # === 3) UNION ALL + 중복 제거 (video_id 기준 최고 점수) ===
    combined = union_all(ts_stmt, trgm_stmt).subquery("combined")

    final_stmt = (
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

    result = await session.execute(final_stmt)
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
            score=float(row.max_score) if row.max_score else 0.0,
        )
        for row in rows
    ]


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
