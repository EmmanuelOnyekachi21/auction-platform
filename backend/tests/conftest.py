"""Pytest configuration and shared fixtures.

Provides an async database session that rolls back after each test and
an ``AsyncClient`` wired to the FastAPI app with the DB dependency
overridden to use that session.
"""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from common.dependency import get_db
from config.database import engine
from main import app


@pytest_asyncio.fixture
async def db_session():
    """Provide a transactional DB session that rolls back after each test.

    Opens a connection, begins a transaction, and yields an ``AsyncSession``
    bound to that connection.  After the test completes the transaction is
    rolled back, leaving the database in its original state.

    Yields:
        An ``AsyncSession`` scoped to a single test transaction.

    """
    async with engine.begin() as conn:
        async with AsyncSession(bind=conn, expire_on_commit=False) as session:
            yield session
            await conn.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    """Yield an async HTTP client backed by the FastAPI app.

    Overrides the ``get_db`` dependency so every request within the test
    uses the transactional ``db_session`` fixture, ensuring database
    operations are isolated and rolled back after each test.

    Args:
        db_session: The transactional ``AsyncSession`` fixture.

    Yields:
        An ``AsyncClient`` configured to call the FastAPI app directly
        via ``ASGITransport``.

    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
