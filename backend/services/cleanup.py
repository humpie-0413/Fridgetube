"""만료 데이터 정리 서비스.

YouTube Developer Policies에 따라 30일 TTL이 지난 데이터를 삭제한다.
대상 테이블: channel_video_index, youtube_video_snapshot
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.video import ChannelVideoIndex, YoutubeVideoSnapshot

logger = logging.getLogger(__name__)


async def cleanup_expired_videos(session: AsyncSession) -> dict[str, int]:
    """만료된 모든 YouTube API 데이터를 삭제.

    Returns:
        {"channel_video_index": N, "youtube_video_snapshot": M}
    """
    now = datetime.now(timezone.utc)
    counts: dict[str, int] = {}

    # channel_video_index
    stmt1 = delete(ChannelVideoIndex).where(ChannelVideoIndex.expires_at < now)
    r1 = await session.execute(stmt1)
    counts["channel_video_index"] = r1.rowcount

    # youtube_video_snapshot
    stmt2 = delete(YoutubeVideoSnapshot).where(YoutubeVideoSnapshot.expires_at < now)
    r2 = await session.execute(stmt2)
    counts["youtube_video_snapshot"] = r2.rowcount

    await session.commit()

    total = sum(counts.values())
    if total > 0:
        logger.info("만료 데이터 삭제: %s", counts)
    else:
        logger.debug("만료 데이터 없음")

    return counts
