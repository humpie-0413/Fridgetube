"""Test fixtures: transactional DB session + mocked external APIs."""

from __future__ import annotations

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from httpx import ASGITransport, AsyncClient

TEST_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/fridgetube"


@pytest.fixture
async def db_session():
    """Create a transactional DB session that rolls back after each test."""
    engine = create_async_engine(TEST_DB_URL, echo=False, connect_args={"ssl": False})
    try:
        connection = await engine.connect()
    except Exception:
        pytest.skip("Database not available")
        return

    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    nested = await connection.begin_nested()

    @event.listens_for(session.sync_session, "after_transaction_end")
    def restart_savepoint(s, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.sync_connection.begin_nested()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()
    await engine.dispose()


@pytest.fixture
async def client(db_session):
    """HTTP test client with transactional DB override."""
    from main import app
    from database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
