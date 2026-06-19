"""Production settings overrides.

These settings override the base Settings class for production deployments.
Never run production with DEBUG=True or publicly accessible API docs.
"""

from config.settings import Settings


class ProductionSettings(Settings):
    """Production-specific settings with stricter defaults."""

    debug: bool = False

    # API docs must never be publicly browsable in production
    docs_url: str | None = None
    redoc_url: str | None = None
    openapi_url: str | None = None

    # Connection pooling for production load
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    database_pool_recycle: int = 1800
