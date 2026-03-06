"""YouTube API 쿼터 예산 관리자.

Redis 기반으로 일일 쿼터 사용량을 추적한다.
YouTube 쿼터는 Pacific Time 자정에 리셋되므로, TTL을 PT 자정까지로 설정한다.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import redis.asyncio as redis

from config import settings

logger = logging.getLogger(__name__)

PACIFIC_TZ = timezone(timedelta(hours=-8))  # PST (서머타임 미적용 기본값)
DAILY_QUOTA_LIMIT = 10_000  # YouTube API v3 무료 쿼터
REDIS_KEY = "yt:quota:daily"


class QuotaBudgeter:
    """Redis 기반 YouTube API 쿼터 카운터."""

    def __init__(
        self,
        redis_client: redis.Redis | None = None,
        daily_limit: int = DAILY_QUOTA_LIMIT,
    ):
        self._redis = redis_client
        self.daily_limit = daily_limit

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    @staticmethod
    def _seconds_until_pacific_midnight() -> int:
        """Pacific Time 자정까지 남은 초 계산."""
        now_pt = datetime.now(PACIFIC_TZ)
        tomorrow_pt = (now_pt + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        delta = tomorrow_pt - now_pt
        return max(int(delta.total_seconds()), 1)

    @staticmethod
    def _today_key() -> str:
        """오늘 날짜 기반 Redis 키 생성 (Pacific Time)."""
        today_pt = datetime.now(PACIFIC_TZ).strftime("%Y-%m-%d")
        return f"{REDIS_KEY}:{today_pt}"

    async def consume(self, units: int = 1) -> int:
        """쿼터를 차감하고 현재 사용량을 반환."""
        r = await self._get_redis()
        key = self._today_key()
        ttl_sec = self._seconds_until_pacific_midnight()

        pipe = r.pipeline()
        pipe.incrby(key, units)
        pipe.expire(key, ttl_sec)
        results = await pipe.execute()
        used = results[0]

        logger.debug("YouTube quota consumed: +%d = %d / %d", units, used, self.daily_limit)
        return used

    async def get_used(self) -> int:
        """오늘 사용한 쿼터."""
        r = await self._get_redis()
        val = await r.get(self._today_key())
        return int(val) if val else 0

    async def get_remaining(self) -> int:
        """남은 쿼터."""
        used = await self.get_used()
        return max(self.daily_limit - used, 0)

    async def get_status(self) -> dict[str, int]:
        """쿼터 상태 요약."""
        used = await self.get_used()
        return {
            "daily_limit": self.daily_limit,
            "used": used,
            "remaining": max(self.daily_limit - used, 0),
        }

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
