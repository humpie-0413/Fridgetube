"""MVP 세션 기반 사용자 관리.

인증 시스템이 없는 MVP에서 X-Session-Id 헤더로 사용자를 구분한다.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User

DEFAULT_SESSION_ID = "default"


async def get_or_create_user(
    session: AsyncSession,
    session_id: str | None = None,
) -> User:
    """세션 ID로 사용자를 조회하거나 새로 생성한다."""
    sid = session_id or DEFAULT_SESSION_ID

    stmt = select(User).where(
        User.provider == "anonymous",
        User.nickname == sid,
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        return user

    user = User(nickname=sid, provider="anonymous")
    session.add(user)
    await session.flush()
    return user
