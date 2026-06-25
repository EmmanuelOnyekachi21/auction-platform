"""Pytest configuration and shared fixtures."""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import config.model_registry  # noqa: F401
from common.dependency import get_db
from config.settings import settings
from main import app

test_engine = create_async_engine(settings.database_url, poolclass=NullPool)


@pytest_asyncio.fixture
async def db_session():
    """Provide a DB session that rolls back after each test."""
    async with test_engine.connect() as connection:
        await connection.begin()
        async with AsyncSession(bind=connection, expire_on_commit=False) as session:
            yield session
        await connection.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    """Async HTTP client with DB dependency overridden to use test session."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
