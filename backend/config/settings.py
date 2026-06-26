"""Application settings and configuration management.

This module defines the global ``Settings`` class used to manage application
configuration via environment variables. It leverages Pydantic for
validation and type safety.
"""

import os
from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings loaded from environment variables.

    Supports automatic loading from a ``.env`` file if present. Configuration
    is categorized into App, Security, Database, Redis, Email, and Cloud
    settings.
    """

    # --- App Identity ---
    app_name: str = "auction-platform"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = False  # opt-in — set DEBUG=True in .env for development
    app_url: str = ""

    # --- Security & JWT ---
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- Persistence ---
    database_url: str
    redis_url: str

    # --- Networking & CORS ---
    cors_origins: str = "http://localhost:3000"
    allowed_hosts: str = "localhost,127.0.0.1"

    mail_from: str

    # --- Resend ---
    resend_api_key: str = ""

    # --- Paystack ---
    paystack_secret_key: str = ""
    paystack_public_key: str = ""
    paystack_base_url: str = "https://api.paystack.co"
    frontend_url: str = ""

    # --- Server URL ---
    server_url: str

    # Cloudinary
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str
    cloudinary_upload_preset: str

    # --- BVN Verification ---
    bvn_verification_enabled: bool = False
    max_auction_duration_hours: int = 24
    min_auction_duration_mins: int = 30

    # --- Transaction Limits
    tier_1_max_bid: Decimal = Decimal("50000.00")
    tier_1_max_wallet_balance: Decimal = Decimal("100000.00")
    tier_1_max_withdrawal: Decimal = Decimal("0.00")

    tier_2_max_bid: Decimal = Decimal("500000.00")
    tier_2_max_wallet_balance: Decimal = Decimal("2000000.00")
    tier_2_max_daily_withdrawal: Decimal = Decimal("500000.00")

    tier_3_max_bid: Decimal = Decimal("999999999.00")
    tier_3_max_wallet_balance: Decimal = Decimal("999999999.00")
    tier_3_max_daily_withdrawal: Decimal = Decimal("5000000.00")

    # Shipping deadline
    shipping_deadline: int

    # SENTRY
    sentry_dsn: str = ""
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.1

    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    database_pool_recycle: int = 1800

    # --- Pydantic Config ---
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def allowed_hosts_list(self) -> list[str]:
        """Parse the ``allowed_hosts`` string into a list of clean strings."""
        return [host.strip() for host in self.allowed_hosts.split(",")]

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse the ``cors_origins`` string into a list of clean strings."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance to be imported by other modules.
def get_settings() -> Settings:
    """Instantiate the appropriate settings class based on the environment.

    Returns ``ProductionSettings`` when ``APP_ENV`` is ``production``,
    otherwise returns the base ``Settings`` instance.

    Returns:
        A configured ``Settings`` (or subclass) instance.

    """
    if os.getenv("APP_ENV", "development") == "production":
        from config.production import (  # local import avoids circular dep
            ProductionSettings,
        )

        return ProductionSettings()
    return Settings()


settings = get_settings()
