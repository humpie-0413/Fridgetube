"""채널 인덱싱 서비스.

YouTube 채널의 uploads 재생목록을 가져와서
channel_video_index 테이블에 저장한다.
tsvector는 DB 트리거 대신 서비스 레벨에서 생성한다.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.channel import YoutubeChannel
from models.video import ChannelVideoIndex
from services.youtube_client import YouTubeClient

logger = logging.getLogger(__name__)

TTL_DAYS = 30
RECIPE_KEYWORDS = re.compile(
    r"레시피|만들기|만드는\s*법|요리법|recipe|cooking|양념|재료|끓이|볶|굽|찜|조림|무침"
)


def _detect_recipe_in_desc(description: str | None) -> bool:
    """설명란에 레시피 관련 키워드가 있는지 판별."""
    if not description:
        return False
    return bool(RECIPE_KEYWORDS.search(description))


class ChannelIndexer:
    """YouTube 채널의 영상을 인덱싱하여 DB에 저장."""

    def __init__(self, yt_client: YouTubeClient, session: AsyncSession):
        self.yt = yt_client
        self.session = session

    async def ensure_channel(self, channel_id: str) -> YoutubeChannel:
        """채널이 DB에 없으면 YouTube API로 조회 후 저장."""
        stmt = select(YoutubeChannel).where(YoutubeChannel.channel_id == channel_id)
        result = await self.session.execute(stmt)
        channel = result.scalar_one_or_none()

        if channel:
            return channel

        yt_data = await self.yt.get_channel(channel_id)
        snippet = yt_data.get("snippet", {})
        stats = yt_data.get("statistics", {})

        channel = YoutubeChannel(
            channel_id=channel_id,
            channel_name=snippet.get("title", ""),
            thumbnail_url=snippet.get("thumbnails", {}).get("default", {}).get("url"),
            subscriber_count=int(stats.get("subscriberCount", 0)) or None,
        )
        self.session.add(channel)
        await self.session.flush()
        return channel

    async def index_channel(
        self,
        channel_id: str,
        video_limit: int = 200,
    ) -> int:
        """채널의 영상을 인덱싱. 추가된 영상 수를 반환."""
        # 1) 채널 확인/생성
        channel = await self.ensure_channel(channel_id)

        # 2) uploads 재생목록 ID 가져오기
        yt_channel = await self.yt.get_channel(channel_id)
        uploads_id = YouTubeClient.extract_uploads_playlist_id(yt_channel)

        # 3) 재생목록 항목 수집
        playlist_items = await self.yt.get_all_playlist_items(uploads_id, limit=video_limit)
        logger.info("Channel %s: fetched %d playlist items", channel.channel_name, len(playlist_items))

        if not playlist_items:
            return 0

        # 4) DB에 upsert
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=TTL_DAYS)
        inserted_count = 0

        for item in playlist_items:
            snippet = item.get("snippet", {})
            content = item.get("contentDetails", {})
            video_id = content.get("videoId") or snippet.get("resourceId", {}).get("videoId")
            if not video_id:
                continue

            title = snippet.get("title", "")
            description = snippet.get("description", "")
            published_at_str = snippet.get("publishedAt")
            published_at = None
            if published_at_str:
                try:
                    published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                except ValueError:
                    pass

            # "Deleted video" / "Private video" 스킵
            if title in ("Deleted video", "Private video"):
                continue

            has_recipe = _detect_recipe_in_desc(description)

            stmt = pg_insert(ChannelVideoIndex).values(
                channel_id=channel.id,
                video_id=video_id,
                title=title,
                description_text=description[:2000] if description else None,
                has_recipe_in_desc=has_recipe,
                published_at=published_at,
                tsv_title=func.to_tsvector("simple", title),
                tsv_description=func.to_tsvector("simple", description[:2000] if description else ""),
                indexed_at=now,
                expires_at=expires,
            ).on_conflict_do_update(
                index_elements=["video_id"],
                set_={
                    "title": title,
                    "description_text": description[:2000] if description else None,
                    "has_recipe_in_desc": has_recipe,
                    "tsv_title": func.to_tsvector("simple", title),
                    "tsv_description": func.to_tsvector("simple", description[:2000] if description else ""),
                    "indexed_at": now,
                    "expires_at": expires,
                },
            )
            await self.session.execute(stmt)
            inserted_count += 1

        # 5) 채널 synced_at 갱신
        channel.synced_at = now
        await self.session.commit()

        logger.info("Channel %s: indexed %d videos", channel.channel_name, inserted_count)
        return inserted_count


async def cleanup_expired(session: AsyncSession) -> int:
    """만료된 channel_video_index 레코드 삭제. 삭제된 수 반환."""
    now = datetime.now(timezone.utc)
    stmt = delete(ChannelVideoIndex).where(ChannelVideoIndex.expires_at < now)
    result = await session.execute(stmt)
    await session.commit()
    count = result.rowcount
    logger.info("Cleaned up %d expired video index records", count)
    return count
