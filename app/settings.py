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
    weather_provider: str = "auto"

    # OpenWeather configuration
    openweather_api_key: str = ""
    openweather_geocode_url: str = "https://api.openweathermap.org/geo/1.0/direct"
    openweather_forecast_url: str = "https://api.openweathermap.org/data/2.5/forecast/daily"

    # Open-Meteo configuration (no key required)
    open_meteo_base_url: str = "https://api.open-meteo.com/v1/forecast"
    open_meteo_geocode_url: str = "https://geocoding-api.open-meteo.com/v1/search"

    # -------- LLM Providers (OpenRouter + NVIDIA) --------
    # If a provider is not configured, the system falls back to deterministic agents.

    llm_provider: str = Field(default="auto")

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-4o-mini"

    # NVIDIA (endpoint/path may vary by product)
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://api.nvidia.com/v1"
    nvidia_model: str = "nvidia/llama-3.1-8b-instruct"

    # NVIDIA chat completions path (optional)
    nvidia_chat_completions_path: str = "chat/completions"

    # Email (optional)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # Tools API key (optional) — simple shared secret for tooling endpoints
    tools_api_key: str = ""
    # Development flag to relax auth for tooling locally
    debug: bool = True


from app.bootstrap import build_settings

# Settings is created in app.bootstrap to allow safe env fallback in local dev/tests.
settings = build_settings()




