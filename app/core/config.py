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

    # Supabase Auth
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    encryption_key: str | None = None

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    use_mock_llm: bool = False

    # Gemini (primary LLM)
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3-flash-preview"
    gemini_api_url: str = "https://generativelanguage.googleapis.com/v1beta"

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
            if not self.supabase_jwt_secret:
                raise ValueError("SUPABASE_JWT_SECRET is required in production.")
            if not self.supabase_service_role_key:
                raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required in production.")
            if not self.supabase_anon_key:
                raise ValueError("SUPABASE_ANON_KEY is required in production.")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins_raw.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
