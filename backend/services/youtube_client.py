"""YouTube Data API v3 래퍼.

channels, playlistItems, videos, commentThreads 엔드포인트를 래핑하며,
모든 호출에서 quota_budgeter를 통해 쿼터를 차감한다.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from config import settings
from services.quota_budgeter import QuotaBudgeter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.googleapis.com/youtube/v3"

# YouTube API 쿼터 비용 (단위: units)
QUOTA_COSTS: dict[str, int] = {
    "channels.list": 1,
    "playlistItems.list": 1,
    "videos.list": 1,
    "search.list": 100,
    "commentThreads.list": 1,
}


class YouTubeQuotaExceeded(Exception):
    pass


class YouTubeAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(message)


class YouTubeClient:
    """YouTube Data API v3 클라이언트."""

    def __init__(self, api_key: str | None = None, budgeter: QuotaBudgeter | None = None):
        self.api_key = api_key or settings.youtube_api_key
        self.budgeter = budgeter

    async def _request(
        self,
        endpoint: str,
        params: dict[str, Any],
        quota_method: str,
    ) -> dict[str, Any]:
        """공통 API 요청 처리."""
        cost = QUOTA_COSTS.get(quota_method, 1)

        if self.budgeter:
            remaining = await self.budgeter.get_remaining()
            if remaining < cost:
                raise YouTubeQuotaExceeded(
                    f"YouTube API 쿼터 부족: 남은={remaining}, 필요={cost}"
                )

        params["key"] = self.api_key
        url = f"{BASE_URL}/{endpoint}"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)

        if resp.status_code != 200:
            error_body = resp.text
            logger.error("YouTube API error %d: %s", resp.status_code, error_body)
            raise YouTubeAPIError(resp.status_code, error_body)

        if self.budgeter:
            await self.budgeter.consume(cost)

        return resp.json()

    # ── channels.list ──

    async def get_channel(self, channel_id: str) -> dict[str, Any]:
        """채널 정보 조회."""
        data = await self._request(
            "channels",
            {"part": "snippet,contentDetails,statistics", "id": channel_id},
            "channels.list",
        )
        items = data.get("items", [])
        if not items:
            raise YouTubeAPIError(404, f"Channel not found: {channel_id}")
        return items[0]

    # ── playlistItems.list ──

    async def get_playlist_items(
        self,
        playlist_id: str,
        max_results: int = 50,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """재생목록 항목 조회 (업로드 목록 등)."""
        params: dict[str, Any] = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": min(max_results, 50),
        }
        if page_token:
            params["pageToken"] = page_token
        return await self._request("playlistItems", params, "playlistItems.list")

    async def get_all_playlist_items(
        self,
        playlist_id: str,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """재생목록의 모든 항목을 페이지네이션으로 수집."""
        items: list[dict[str, Any]] = []
        page_token = None

        while len(items) < limit:
            data = await self.get_playlist_items(
                playlist_id, max_results=50, page_token=page_token
            )
            items.extend(data.get("items", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return items[:limit]

    # ── videos.list ──

    async def get_videos(self, video_ids: list[str]) -> list[dict[str, Any]]:
        """비디오 상세 정보 조회 (최대 50개)."""
        if not video_ids:
            return []
        data = await self._request(
            "videos",
            {
                "part": "snippet,contentDetails,statistics",
                "id": ",".join(video_ids[:50]),
            },
            "videos.list",
        )
        return data.get("items", [])

    # ── commentThreads.list ──

    async def get_comment_threads(
        self,
        video_id: str,
        max_results: int = 100,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """비디오 댓글 스레드 조회."""
        params: dict[str, Any] = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(max_results, 100),
            "order": "relevance",
        }
        if page_token:
            params["pageToken"] = page_token
        return await self._request("commentThreads", params, "commentThreads.list")

    # ── search.list ──

    async def search_videos(
        self,
        query: str,
        max_results: int = 10,
        page_token: str | None = None,
        channel_id: str | None = None,
    ) -> dict[str, Any]:
        """YouTube 검색 (100 units/call — 신중히 사용)."""
        params: dict[str, Any] = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": min(max_results, 50),
            "relevanceLanguage": "ko",
            "regionCode": "KR",
        }
        if page_token:
            params["pageToken"] = page_token
        if channel_id:
            params["channelId"] = channel_id
        return await self._request("search", params, "search.list")

    # ── channels search (search.list with type=channel) ──

    async def search_channels(
        self,
        query: str,
        max_results: int = 5,
    ) -> dict[str, Any]:
        """YouTube 채널 검색 (search.list, 100 units/call)."""
        params: dict[str, Any] = {
            "part": "snippet",
            "q": query,
            "type": "channel",
            "maxResults": min(max_results, 10),
        }
        return await self._request("search", params, "search.list")

    # ── 유틸리티 ──

    @staticmethod
    def extract_uploads_playlist_id(channel_data: dict[str, Any]) -> str:
        """채널 데이터에서 uploads 재생목록 ID 추출."""
        return channel_data["contentDetails"]["relatedPlaylists"]["uploads"]
