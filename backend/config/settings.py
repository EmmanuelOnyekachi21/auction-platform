"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # APP
    app_name: str = "auction-platform"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = True

    # Security
    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Database
    database_url: str

    # Redis
    redis_url: str

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Hosts
    allowed_hosts: str = "localhost,127.0.0.1"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    @property
    def allowed_hosts_list(self) -> list[str]:
        """Return allowed hosts as a list."""
        return [host.strip() for host in self.allowed_hosts.split(",")]

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
