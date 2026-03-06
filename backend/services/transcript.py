"""레시피 텍스트 수집 서비스 — 3단계 정식 경로.

1순위: 설명란 텍스트 (channel_video_index.description_text)
2순위: 작성자 댓글 (author_comment.py → commentThreads 1 unit)
3순위: Flow D 안내 반환 ("설명란/댓글에서 레시피를 찾지 못했습니다")

비공식 자막(youtube-transcript-api) 코드 작성 금지.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.video import ChannelVideoIndex, YoutubeVideoSnapshot
from services.author_comment import get_author_comments
from services.quota_budgeter import QuotaBudgeter
from services.text_compressor import compress, truncate
from services.youtube_client import YouTubeClient

logger = logging.getLogger(__name__)

# 레시피 텍스트로 인정할 최소 길이
MIN_RECIPE_LENGTH = 30

# 레시피 관련 키워드 (설명란/댓글에 이 키워드가 있으면 레시피 포함 가능성 높음)
_RECIPE_KEYWORDS = [
    "재료", "양념", "만들기", "레시피", "인분", "큰술", "작은술",
    "g ", "ml ", "컵", "개", "소스", "준비물", "조리법",
    "recipe", "ingredient", "tbsp", "tsp",
]


@dataclass
class TranscriptResult:
    """레시피 텍스트 수집 결과."""

    text: str
    source: str  # "description" | "author_comment" | "flow_d"
    has_recipe_hint: bool  # 레시피 키워드 포함 여부


FLOW_D_MESSAGE = (
    "설명란과 댓글에서 레시피 정보를 찾지 못했습니다. "
    "영상을 직접 시청하시거나, 레시피 텍스트를 수동으로 입력해 주세요."
)


def _has_recipe_keywords(text: str) -> bool:
    """텍스트에 레시피 관련 키워드가 포함되어 있는지 확인."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in _RECIPE_KEYWORDS)


async def collect_transcript(
    session: AsyncSession,
    video_id: str,
    *,
    youtube_client: YouTubeClient | None = None,
    budgeter: QuotaBudgeter | None = None,
) -> TranscriptResult:
    """3단계 경로로 레시피 텍스트를 수집한다.

    Args:
        session: DB 세션
        video_id: YouTube 영상 ID
        youtube_client: YouTubeClient 인스턴스
        budgeter: QuotaBudgeter 인스턴스

    Returns:
        TranscriptResult
    """
    # ── 1순위: 설명란 텍스트 ──
    stmt = select(ChannelVideoIndex).where(ChannelVideoIndex.video_id == video_id)
    result = await session.execute(stmt)
    video_index = result.scalar_one_or_none()

    if video_index and video_index.description_text:
        desc = compress(video_index.description_text)
        if len(desc) >= MIN_RECIPE_LENGTH and _has_recipe_keywords(desc):
            logger.info("Recipe text found in description for %s", video_id)
            return TranscriptResult(
                text=truncate(desc),
                source="description",
                has_recipe_hint=True,
            )

    # ── 2순위: 작성자 댓글 ──
    yt_channel_id = await _get_yt_channel_id(session, video_id, video_index)
    if yt_channel_id:
        comments = await get_author_comments(
            video_id,
            yt_channel_id,
            youtube_client=youtube_client,
            budgeter=budgeter,
        )
        if comments:
            # 가장 긴 댓글 또는 레시피 키워드가 있는 댓글 우선
            best = _pick_best_comment(comments)
            if best and len(best) >= MIN_RECIPE_LENGTH:
                compressed = compress(best)
                logger.info("Recipe text found in author comment for %s", video_id)
                return TranscriptResult(
                    text=truncate(compressed),
                    source="author_comment",
                    has_recipe_hint=_has_recipe_keywords(compressed),
                )

    # ── 설명란이 있지만 키워드가 없는 경우, 그래도 Gemini에게 시도 ──
    if video_index and video_index.description_text:
        desc = compress(video_index.description_text)
        if len(desc) >= MIN_RECIPE_LENGTH:
            logger.info("Sending description without recipe keywords for %s", video_id)
            return TranscriptResult(
                text=truncate(desc),
                source="description",
                has_recipe_hint=False,
            )

    # ── 3순위: Flow D ──
    logger.info("No recipe text found for %s, returning Flow D", video_id)
    return TranscriptResult(
        text=FLOW_D_MESSAGE,
        source="flow_d",
        has_recipe_hint=False,
    )


def _pick_best_comment(comments: list[str]) -> str | None:
    """댓글 중 레시피 가능성이 가장 높은 것을 선택."""
    # 레시피 키워드가 있는 댓글 우선
    for comment in comments:
        if _has_recipe_keywords(comment):
            return comment
    # 없으면 가장 긴 댓글
    return max(comments, key=len) if comments else None


async def _get_yt_channel_id(
    session: AsyncSession,
    video_id: str,
    video_index: ChannelVideoIndex | None,
) -> str | None:
    """YouTube 채널 ID를 조회. snapshot 또는 channel 테이블에서."""
    # 1) youtube_video_snapshot에서
    stmt = select(YoutubeVideoSnapshot.yt_channel_id).where(
        YoutubeVideoSnapshot.video_id == video_id
    )
    result = await session.execute(stmt)
    yt_ch_id = result.scalar_one_or_none()
    if yt_ch_id:
        return yt_ch_id

    # 2) channel_video_index → youtube_channels에서
    if video_index:
        from models.channel import YoutubeChannel

        stmt2 = select(YoutubeChannel.channel_id).where(
            YoutubeChannel.id == video_index.channel_id
        )
        result2 = await session.execute(stmt2)
        return result2.scalar_one_or_none()

    return None
