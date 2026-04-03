"""Application settings and configuration management.

This module defines the global ``Settings`` class used to manage application
configuration via environment variables. It leverages Pydantic for
validation and type safety.
"""

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
    debug: bool = True
    app_url: str

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

    # --- Email (SMTP) ---
    mail_username: str
    mail_password: str
    mail_from: str = "noreply@auction-platform.com"
    mail_port: int
    mail_server: str
    mail_from_name: str = "Auction Platform"
    mail_starttls: bool = True
    mail_ssl_tls: bool = False

    # --- Resend ---
    resend_api_key: str = ""

    # --- Brevo ---
    brevo_api_key: str = ""

    # --- Flutterwave ---
    flutterwave_secret_key: str = ""
    flutterwave_public_key: str = ""  # You'll need this for frontend integration later
    flutterwave_base_url: str = "https://api.flutterwave.com/v3"
    flutterwave_webhook_secret: str = ""
    frontend_url: str = ""

    # --- Server URL ---
    server_url: str

    # Cloudinary
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str
    cloudinary_upload_preset: str

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
settings = Settings()
