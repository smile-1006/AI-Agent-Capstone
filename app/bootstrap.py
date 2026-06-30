"""Runtime bootstrap helpers."""

from __future__ import annotations

import os

from app.settings import Settings



def build_settings() -> Settings:
    """Build Settings safely.

    During local dev and unit tests, .env may not be present.
    We provide a sane fallback for jwt_secret so imports don't fail.
    """

    raw_env = dict(os.environ)

    # Ensure required secrets exist for local runs.
    jwt_secret = raw_env.get("JWT_SECRET") or "dev-only-change-me"
    raw_env.setdefault("JWT_SECRET", jwt_secret)

    # Prefer to let pydantic load .env values automatically.
    try:
        return Settings()
    except Exception:
        # If .env parsing or validation fails, fall back to explicit env values.
        return Settings(
            app_env=raw_env.get("APP_ENV", "development"),
            port=int(raw_env.get("PORT", "8000")),
            jwt_secret=jwt_secret,
            jwt_algorithm=raw_env.get("JWT_ALGORITHM", "HS256"),
            access_token_expires_minutes=int(raw_env.get("ACCESS_TOKEN_EXPIRES_MINUTES", "60")),
            rate_limit_per_minute=int(raw_env.get("RATE_LIMIT_PER_MINUTE", "120")),
            database_url=raw_env.get("DATABASE_URL", "sqlite:///./database/sqlite.db"),
            log_level=raw_env.get("LOG_LEVEL", "INFO"),
            embeddings_dim=int(raw_env.get("EMBEDDINGS_DIM", str(384))),
            embeddings_top_k=int(raw_env.get("EMBEDDINGS_TOP_K", str(5))),
            web_search_api_url=raw_env.get("WEB_SEARCH_API_URL", ""),
            weather_api_url=raw_env.get("WEATHER_API_URL", ""),
            openweather_api_key=raw_env.get("OPENWEATHER_API_KEY", ""),
            openweather_geocode_url=raw_env.get(
                "OPENWEATHER_GEOCODE_URL", "https://api.openweathermap.org/geo/1.0/direct"
            ),
            openweather_forecast_url=raw_env.get(
                "OPENWEATHER_FORECAST_URL", "https://api.openweathermap.org/data/2.5/forecast/daily"
            ),
            tools_api_key=raw_env.get("TOOLS_API_KEY", ""),
            smtp_host=raw_env.get("SMTP_HOST", ""),
            smtp_port=int(raw_env.get("SMTP_PORT", "587")),
            smtp_user=raw_env.get("SMTP_USER", ""),
            smtp_password=raw_env.get("SMTP_PASSWORD", ""),
            smtp_from=raw_env.get("SMTP_FROM", ""),
            llm_provider=raw_env.get("LLM_PROVIDER", "auto"),
            openrouter_api_key=raw_env.get("OPENROUTER_API_KEY", ""),
            openrouter_base_url=raw_env.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            openrouter_model=raw_env.get("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
            nvidia_api_key=raw_env.get("NVIDIA_API_KEY", ""),
            nvidia_base_url=raw_env.get("NVIDIA_BASE_URL", "https://api.nvidia.com/v1"),
            nvidia_model=raw_env.get("NVIDIA_MODEL", "nvidia/llama-3.1-8b-instruct"),
            nvidia_chat_completions_path=raw_env.get(
                "NVIDIA_CHAT_COMPLETIONS_PATH", "chat/completions"
            ),
        )




