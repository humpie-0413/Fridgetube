"""영상 업로더의 댓글 필터링 서비스.

commentThreads.list API를 사용하여 영상 작성자 본인이 단 댓글만 추출한다.
요리 채널에서 재료/레시피를 댓글에 고정하는 경우가 많으므로 핵심 소스.
YouTube API 쿼터: commentThreads.list = 1 unit/call.
"""

from __future__ import annotations

import logging

from services.quota_budgeter import QuotaBudgeter
from services.youtube_client import YouTubeAPIError, YouTubeClient, YouTubeQuotaExceeded

logger = logging.getLogger(__name__)


async def get_author_comments(
    video_id: str,
    yt_channel_id: str,
    *,
    youtube_client: YouTubeClient | None = None,
    budgeter: QuotaBudgeter | None = None,
    max_results: int = 20,
) -> list[str]:
    """영상 업로더(authorChannelId)가 작성한 댓글 텍스트를 반환한다.

    Args:
        video_id: YouTube 영상 ID
        yt_channel_id: 영상 업로더의 YouTube 채널 ID
        youtube_client: YouTubeClient 인스턴스 (없으면 생성)
        budgeter: QuotaBudgeter 인스턴스 (쿼터 체크용)
        max_results: 조회할 댓글 스레드 수

    Returns:
        업로더 댓글 텍스트 리스트 (빈 리스트 = 댓글 없음)
    """
    client = youtube_client or YouTubeClient(budgeter=budgeter)

    try:
        data = await client.get_comment_threads(video_id, max_results=max_results)
    except YouTubeQuotaExceeded:
        logger.warning("YouTube quota exceeded, skipping author comments for %s", video_id)
        return []
    except YouTubeAPIError as e:
        # 댓글 비활성화 등 403/404 에러
        if e.status_code in (403, 404):
            logger.info("Comments unavailable for video %s: %s", video_id, e)
            return []
        raise

    author_texts: list[str] = []
    for item in data.get("items", []):
        snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
        comment_author_id = snippet.get("authorChannelId", {}).get("value", "")
        if comment_author_id == yt_channel_id:
            text = snippet.get("textDisplay", "").strip()
            if text:
                author_texts.append(text)

    logger.info(
        "Found %d author comments for video %s (channel %s)",
        len(author_texts),
        video_id,
        yt_channel_id,
    )
    return author_texts
