"""Application settings.

This module defines strongly-typed configuration loaded from environment
variables (optionally from a .env file).

Production notes:
- Keep settings immutable after initialization.
- Validate early so the app fails fast on misconfiguration.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Server
    app_env: str = Field(default="development")
    port: int = Field(default=8000)

    # Security
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 60

    # Rate limiting
    rate_limit_per_minute: int = 120

    # Database
    database_url: str = "sqlite:///./database/sqlite.db"

    # Observability
    log_level: str = "INFO"

    # Embeddings (local embedding implementation)
    embeddings_dim: int = 384
    embeddings_top_k: int = 5

    # External tool endpoints (optional)
    web_search_api_url: str = ""
    weather_api_url: str = ""

    # Email (optional)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""


from app.bootstrap import build_settings

# Settings is created in app.bootstrap to allow safe env fallback in local dev/tests.
settings = build_settings()




