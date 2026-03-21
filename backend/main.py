"""Auction platform FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from common.exception_handlers import (
    handle_auction_platform_exception,
    handle_generic_exception,
    handle_not_found,
    handle_pydantic_validation_error,
)
from common.exceptions import AuctionPlatformException
from common.middleware import RequestLoggingMiddleware
from config.database import engine
from config.logging_config import setup_logging
from config.settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events.

    Handles startup and shutdown operations.

    Args:
        app: FastAPI application instance.

    Yields:
        None: Control to the application during its runtime.

    """
    setup_logging(settings.app_env)
    logger.info(
        "Starting %s v%s [%s]",
        settings.app_name,
        settings.app_version,
        settings.app_env,
    )

    # Verify database connection
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception:
        logger.error("Database connection failed", exc_info=True)

    # Verify Redis connection
    try:
        redis_client = aioredis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.aclose()
        logger.info("Redis connection verified")
    except Exception:
        logger.error("Redis connection failed", exc_info=True)

    yield

    # Shutdown
    logger.info("Shutting down %s", settings.app_name)
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.app_env != "production" else None,
    redoc_url="/api/redoc" if settings.app_env != "production" else None,
    openapi_url="/api/openapi.json" if settings.app_env != "production" else None,
)

# --- Middleware ---
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Exception handlers ---
app.add_exception_handler(AuctionPlatformException, handle_auction_platform_exception)
app.add_exception_handler(RequestValidationError, handle_pydantic_validation_error)
app.add_exception_handler(HTTPException, handle_not_found)
app.add_exception_handler(Exception, handle_generic_exception)


async def _check_db() -> bool:
    """Return True if the database is reachable."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _check_redis() -> bool:
    """Return True if Redis is reachable."""
    try:
        redis_client = aioredis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.aclose()
        return True
    except Exception:
        return False


@app.get("/health")
async def health():
    """Return application health status."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "database_connected": await _check_db(),
        "redis_connected": await _check_redis(),
    }


@app.get("/api/v1/health")
async def health_v1():
    """Return application health status for API v1."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "database_connected": await _check_db(),
        "redis_connected": await _check_redis(),
    }
