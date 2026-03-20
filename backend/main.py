"""Auction platform FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from common.exception_handlers import (
    handle_auction_platform_exception,
    handle_generic_exception,
    handle_not_found,
    handle_pydantic_validation_error,
)
from common.exceptions import AuctionPlatformException
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
    logger.info("Application starting up...")
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(AuctionPlatformException, handle_auction_platform_exception)
app.add_exception_handler(RequestValidationError, handle_pydantic_validation_error)
app.add_exception_handler(HTTPException, handle_not_found)
app.add_exception_handler(Exception, handle_generic_exception)


@app.get("/health")
async def health():
    """Return application health status."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@app.get("/api/v1/health")
async def health_v1():
    """Return application health status for API v1."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }
