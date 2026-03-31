from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RedditFlow"
    environment: str = "development"
    database_url: str = "sqlite:///./poacher.db"
    auto_create_tables: bool = True

    frontend_url: str = "http://localhost:3000"
    cors_origins_raw: str = "http://localhost:3000,http://127.0.0.1:3000"
    jwt_secret: str = "change-me-in-production-32-bytes-min"
    jwt_algorithm: str = "HS256"
    jwt_exp_minutes: int = 60 * 24
    encryption_key: str | None = None

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    use_mock_llm: bool = False

    # Gemini (primary LLM)
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3-flash-preview"
    gemini_api_url: str = "https://generativelanguage.googleapis.com/v1beta"

    reddit_base_url: str = "https://www.reddit.com"
    reddit_user_agent: str = "redditflow/1.0"

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
            if self.jwt_secret == "change-me-in-production-32-bytes-min":
                raise ValueError("JWT_SECRET must be changed from default in production.")
            if len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET must be at least 32 characters.")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins_raw.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
