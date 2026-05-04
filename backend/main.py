"""Auction platform FastAPI application entry point.

This module initializes the FastAPI app instance, configures middleware,
registers global exception handlers, and mounts the application routers.
It also manages startup/shutdown lifespan events, including connection
verification for PostgreSQL and Redis.
"""

import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

# Import the model registry to ensure all models are registered with SQLAlchemy
# before any logic tries to use them.
import config.model_registry  # noqa: F401
from apps.admin.setup import create_admin
from apps.auctions.routers import router as auctions_router
from apps.authentication.routers import router as auth_router
from apps.bids.router import router as bids_router
from apps.disputes.router import router as disputes_router
from apps.notifications.routers import router as notifications_router
from apps.orders.router import router as orders_router
from apps.users.kyc_router import router as kyc_router
from apps.users.routers import router as users_router
from apps.wallet.routers import router as wallet_router
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

    Performs initialization (logging, connection pings) on startup and
    cleanup (session disposal) on shutdown.

    Args:
        app: The current FastAPI instance.

    Yields:
        None: Control to the application until shutdown.

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


# Core Application setup
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.app_env != "production" else None,
    redoc_url="/api/redoc" if settings.app_env != "production" else None,
    openapi_url="/api/openapi.json" if settings.app_env != "production" else None,
)

# --- Global Middleware ---
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Exception Handlers ---
app.add_exception_handler(AuctionPlatformException, handle_auction_platform_exception)
app.add_exception_handler(RequestValidationError, handle_pydantic_validation_error)
app.add_exception_handler(HTTPException, handle_not_found)
app.add_exception_handler(Exception, handle_generic_exception)

# --- API Routers ---
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
app.include_router(kyc_router, prefix="/api/v1/kyc", tags=["KYC"])
app.include_router(
    notifications_router, prefix="/api/v1/notifications", tags=["Notifications"]
)
app.include_router(wallet_router, prefix="/api/v1/wallets", tags=["Wallets"])
app.include_router(auctions_router, prefix="/api/v1", tags=["Auctions"])
app.include_router(bids_router, prefix="/api/v1", tags=["Bids"])
app.include_router(orders_router, prefix="/api/v1", tags=["Orders"])
app.include_router(disputes_router, prefix="/api/v1", tags=["Disputes"])

# --- Admin Panel ---
admin = create_admin(app)


# --- Utility Helpers ---
async def _check_db() -> bool:
    """Check if the PostgreSQL database is reachable.

    Returns:
        bool: True if database connection is successful, False otherwise.

    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _check_redis() -> bool:
    """Check if the Redis server is reachable.

    Returns:
        bool: True if Redis connection is successful, False otherwise.

    """
    try:
        redis_client = aioredis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.aclose()
        return True
    except Exception:
        return False


# --- Health Endpoints ---
@app.get("/health")
async def health() -> dict:
    """Return application health status used for readiness probes.

    Returns:
        dict: Infrastructure connectivity and app version info.

    """
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "database_connected": await _check_db(),
        "redis_connected": await _check_redis(),
    }


@app.get("/api/v1/health")
async def health_v1() -> dict:
    """Versioned health checkpoint for consistency within /api/v1.

    Returns:
        dict: Identical payload to root /health.

    """
    return await health()
