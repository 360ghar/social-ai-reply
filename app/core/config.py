from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants.app import (
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_GEMINI_API_URL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_PERPLEXITY_MODEL,
)


class Settings(BaseSettings):
    app_name: str = "RedditFlow"
    environment: str = "development"
    database_url: str = "sqlite:///./poacher.db"
    auto_create_tables: bool = True

    frontend_url: str = "http://localhost:3000"
    cors_origins_raw: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Supabase Auth
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    supabase_jwt_secret: str = ""

    encryption_key: str | None = None

    # LLM Provider selection — Gemini is the default for RedditFlow.
    # See app/core/constants/app.py::DEFAULT_LLM_PROVIDER. Only the active
    # provider's credentials are required; the registry silently skips any
    # provider whose API key is missing.
    llm_provider: str = DEFAULT_LLM_PROVIDER

    # Gemini (primary — default provider, normally the only one configured)
    gemini_api_key: str | None = None
    gemini_model: str = DEFAULT_GEMINI_MODEL
    gemini_api_url: str = DEFAULT_GEMINI_API_URL

    # OpenAI (optional alternative — leave unset unless llm_provider="openai")
    openai_api_key: str | None = None
    openai_model: str = DEFAULT_OPENAI_MODEL
    openai_base_url: str | None = None

    # Perplexity (optional alternative)
    perplexity_api_key: str | None = None
    perplexity_model: str = DEFAULT_PERPLEXITY_MODEL

    # Anthropic / Claude (optional alternative)
    anthropic_api_key: str | None = None
    anthropic_model: str = DEFAULT_ANTHROPIC_MODEL

    reddit_base_url: str = "https://www.reddit.com"
    reddit_user_agent: str = "web:redditflow:v1.2 (by /u/redditflow_bot)"

    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_publishable_key: str | None = None

    smtp_from_email: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.environment == "production":
            if not self.supabase_url:
                raise ValueError("SUPABASE_URL is required in production.")
            if not self.supabase_secret_key:
                raise ValueError("SUPABASE_SECRET_KEY is required in production.")
            if not self.supabase_publishable_key:
                raise ValueError("SUPABASE_PUBLISHABLE_KEY is required in production.")
            if not self.supabase_jwt_secret:
                raise ValueError("SUPABASE_JWT_SECRET is required in production.")
            if not self.encryption_key:
                raise ValueError("ENCRYPTION_KEY is required in production.")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins_raw.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
