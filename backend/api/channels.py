"""선호 채널 관리 API.

GET  /v1/channels/search?q=       YouTube 채널 검색
POST /v1/channels/favorites       선호 채널 추가
GET  /v1/channels/favorites       선호 채널 목록
DELETE /v1/channels/favorites/{channel_id}  선호 채널 삭제
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.session_user import get_or_create_user
from database import get_db
from models.channel import YoutubeChannel
from models.user import UserFavoriteChannel
from services.quota_budgeter import QuotaBudgeter
from services.youtube_client import YouTubeAPIError, YouTubeClient, YouTubeQuotaExceeded

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/channels", tags=["channels"])


# ── 스키마 ──


class ChannelSearchItem(BaseModel):
    channel_id: str
    name: str
    thumbnail_url: str | None = None
    subscriber_count: int | None = None
    description: str | None = None


class ChannelSearchResponse(BaseModel):
    channels: list[ChannelSearchItem]


class FavoriteChannelItem(BaseModel):
    id: str
    channel_id: str
    channel_name: str
    thumbnail_url: str | None = None
    subscriber_count: int | None = None


class FavoritesResponse(BaseModel):
    favorites: list[FavoriteChannelItem]


class AddFavoriteRequest(BaseModel):
    channel_id: str = Field(..., min_length=1, max_length=50)


class AddFavoriteResponse(BaseModel):
    id: str
    channel_id: str
    channel_name: str


# ── 엔드포인트 ──


@router.get("/search", response_model=ChannelSearchResponse)
async def search_channels(
    q: str = Query(..., min_length=1, max_length=100, description="채널 검색어"),
    limit: int = Query(default=5, ge=1, le=10),
) -> ChannelSearchResponse:
    """YouTube 채널 검색 (search.list, 100 units/call)."""
    try:
        budgeter = QuotaBudgeter()
        yt = YouTubeClient(budgeter=budgeter)
        data = await yt.search_channels(q, max_results=limit)
    except YouTubeQuotaExceeded:
        raise HTTPException(
            status_code=429,
            detail={"error": {"code": "QUOTA_EXCEEDED", "message": "YouTube API 쿼터 초과", "details": {}}},
        )
    except YouTubeAPIError as e:
        raise HTTPException(
            status_code=502,
            detail={"error": {"code": "YOUTUBE_ERROR", "message": str(e), "details": {}}},
        )

    items = data.get("items", [])
    channels = []
    for item in items:
        snippet = item.get("snippet", {})
        thumbnails = snippet.get("thumbnails", {})
        thumb = thumbnails.get("default", {}).get("url")
        channels.append(
            ChannelSearchItem(
                channel_id=item.get("id", {}).get("channelId", "")
                if isinstance(item.get("id"), dict)
                else item.get("snippet", {}).get("channelId", ""),
                name=snippet.get("channelTitle", snippet.get("title", "")),
                thumbnail_url=thumb,
                description=snippet.get("description", ""),
            )
        )
    return ChannelSearchResponse(channels=channels)


@router.post("/favorites", response_model=AddFavoriteResponse)
async def add_favorite_channel(
    req: AddFavoriteRequest,
    session: AsyncSession = Depends(get_db),
    x_session_id: str | None = Header(None),
) -> AddFavoriteResponse:
    """선호 채널 추가. YoutubeChannel이 없으면 YouTube API로 조회 후 저장."""
    user = await get_or_create_user(session, x_session_id)

    # 1) youtube_channels 테이블에 존재하는지 확인
    stmt = select(YoutubeChannel).where(YoutubeChannel.channel_id == req.channel_id)
    result = await session.execute(stmt)
    channel = result.scalar_one_or_none()

    if not channel:
        # YouTube API로 채널 정보 조회
        try:
            yt = YouTubeClient()
            ch_data = await yt.get_channel(req.channel_id)
        except YouTubeAPIError:
            raise HTTPException(
                status_code=404,
                detail={"error": {"code": "CHANNEL_NOT_FOUND", "message": "채널을 찾을 수 없습니다", "details": {}}},
            )

        snippet = ch_data.get("snippet", {})
        stats = ch_data.get("statistics", {})
        channel = YoutubeChannel(
            channel_id=req.channel_id,
            channel_name=snippet.get("title", ""),
            thumbnail_url=snippet.get("thumbnails", {}).get("default", {}).get("url"),
            subscriber_count=int(stats.get("subscriberCount", 0)) if stats.get("subscriberCount") else None,
        )
        session.add(channel)
        await session.flush()

    # 2) 이미 즐겨찾기인지 확인
    fav_stmt = select(UserFavoriteChannel).where(
        UserFavoriteChannel.user_id == user.id,
        UserFavoriteChannel.channel_id == channel.id,
    )
    fav_result = await session.execute(fav_stmt)
    existing = fav_result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "ALREADY_FAVORITED", "message": "이미 즐겨찾기에 추가된 채널입니다", "details": {}}},
        )

    # 3) 즐겨찾기 추가
    fav = UserFavoriteChannel(user_id=user.id, channel_id=channel.id)
    session.add(fav)
    await session.commit()

    return AddFavoriteResponse(
        id=str(fav.id),
        channel_id=req.channel_id,
        channel_name=channel.channel_name,
    )


@router.get("/favorites", response_model=FavoritesResponse)
async def list_favorite_channels(
    session: AsyncSession = Depends(get_db),
    x_session_id: str | None = Header(None),
) -> FavoritesResponse:
    """선호 채널 목록 조회."""
    user = await get_or_create_user(session, x_session_id)

    stmt = (
        select(UserFavoriteChannel, YoutubeChannel)
        .join(YoutubeChannel, UserFavoriteChannel.channel_id == YoutubeChannel.id)
        .where(UserFavoriteChannel.user_id == user.id)
        .order_by(UserFavoriteChannel.created_at.desc())
    )
    result = await session.execute(stmt)
    rows = result.all()

    favorites = [
        FavoriteChannelItem(
            id=str(fav.id),
            channel_id=ch.channel_id,
            channel_name=ch.channel_name,
            thumbnail_url=ch.thumbnail_url,
            subscriber_count=ch.subscriber_count,
        )
        for fav, ch in rows
    ]
    return FavoritesResponse(favorites=favorites)


@router.delete("/favorites/{channel_id}")
async def remove_favorite_channel(
    channel_id: str,
    session: AsyncSession = Depends(get_db),
    x_session_id: str | None = Header(None),
) -> dict:
    """선호 채널 삭제. channel_id는 YouTube 채널 ID (UCxxx)."""
    user = await get_or_create_user(session, x_session_id)

    # YoutubeChannel의 DB id를 먼저 조회
    ch_stmt = select(YoutubeChannel.id).where(YoutubeChannel.channel_id == channel_id)
    ch_result = await session.execute(ch_stmt)
    ch_db_id = ch_result.scalar_one_or_none()

    if not ch_db_id:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "CHANNEL_NOT_FOUND", "message": "채널을 찾을 수 없습니다", "details": {}}},
        )

    stmt = delete(UserFavoriteChannel).where(
        UserFavoriteChannel.user_id == user.id,
        UserFavoriteChannel.channel_id == ch_db_id,
    )
    result = await session.execute(stmt)
    await session.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FAVORITED", "message": "즐겨찾기에 없는 채널입니다", "details": {}}},
        )

    return {"deleted": True, "channel_id": channel_id}
