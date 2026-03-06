"""배치 채널 인덱싱 CLI.

Usage:
    # 큐레이션 채널 전체 인덱싱
    python -m cli.index_channels

    # 특정 채널만 인덱싱
    python -m cli.index_channels --channel-id UCyn-K7rZLXjGl7VXGweIlcA

    # 만료 데이터 정리만
    python -m cli.index_channels --cleanup-only

    # 채널당 영상 수 제한
    python -m cli.index_channels --limit 100
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# backend/ 디렉토리를 모듈 경로에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import async_session
from services.channel_index import ChannelIndexer, cleanup_expired
from services.quota_budgeter import QuotaBudgeter
from services.youtube_client import YouTubeClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

SEEDS_PATH = Path(__file__).resolve().parent.parent / "seeds" / "curated_channels.json"


def load_curated_channels() -> list[dict]:
    with open(SEEDS_PATH, encoding="utf-8") as f:
        return json.load(f)


async def run_index(
    channel_ids: list[str] | None = None,
    video_limit: int = 200,
    cleanup: bool = True,
) -> None:
    budgeter = QuotaBudgeter()
    yt_client = YouTubeClient(budgeter=budgeter)

    try:
        # 1) 만료 데이터 정리
        if cleanup:
            async with async_session() as session:
                deleted = await cleanup_expired(session)
                if deleted > 0:
                    logger.info("만료 데이터 %d건 삭제 완료", deleted)

        # 2) 인덱싱 대상 결정
        if channel_ids:
            targets = [{"channel_id": cid, "name": cid} for cid in channel_ids]
        else:
            targets = load_curated_channels()

        logger.info("인덱싱 대상: %d개 채널", len(targets))

        # 3) 쿼터 확인
        status = await budgeter.get_status()
        logger.info("YouTube 쿼터: %d / %d 사용", status["used"], status["daily_limit"])

        # 4) 채널별 인덱싱
        total_videos = 0
        for i, ch in enumerate(targets, 1):
            cid = ch["channel_id"]
            name = ch.get("name", cid)

            remaining = await budgeter.get_remaining()
            # 채널당 최소 3 units (channel + playlistItems pages)
            if remaining < 3:
                logger.warning("쿼터 부족으로 중단. 남은 쿼터: %d", remaining)
                break

            logger.info("[%d/%d] %s (%s) 인덱싱 시작...", i, len(targets), name, cid)

            try:
                async with async_session() as session:
                    indexer = ChannelIndexer(yt_client, session)
                    count = await indexer.index_channel(cid, video_limit=video_limit)
                    total_videos += count
                    logger.info("[%d/%d] %s: %d개 영상 인덱싱 완료", i, len(targets), name, count)
            except Exception:
                logger.exception("[%d/%d] %s 인덱싱 실패", i, len(targets), name)

        logger.info("전체 인덱싱 완료: %d개 영상", total_videos)
        final_status = await budgeter.get_status()
        logger.info("최종 쿼터: %d / %d 사용", final_status["used"], final_status["daily_limit"])

    finally:
        await budgeter.close()


async def run_cleanup_only() -> None:
    async with async_session() as session:
        deleted = await cleanup_expired(session)
        logger.info("만료 데이터 %d건 삭제 완료", deleted)


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube 채널 인덱싱 CLI")
    parser.add_argument(
        "--channel-id",
        type=str,
        nargs="+",
        help="특정 채널 ID만 인덱싱",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="채널당 최대 영상 수 (기본: 200)",
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="만료 데이터 정리만 실행",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="만료 데이터 정리 건너뛰기",
    )
    args = parser.parse_args()

    if args.cleanup_only:
        asyncio.run(run_cleanup_only())
    else:
        asyncio.run(
            run_index(
                channel_ids=args.channel_id,
                video_limit=args.limit,
                cleanup=not args.no_cleanup,
            )
        )


if __name__ == "__main__":
    main()
