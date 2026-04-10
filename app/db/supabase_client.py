"""Supabase client module for database operations.

This module provides a singleton Supabase client and FastAPI dependency
for use throughout the application.
"""

from collections.abc import Generator
from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Get or create the singleton Supabase client instance.

    Returns:
        Configured Supabase client instance.

    Raises:
        ValueError: If Supabase URL or secret key is not configured.
    """
    settings = get_settings()

    if not settings.supabase_url:
        raise ValueError("SUPABASE_URL is not configured")
    if not settings.supabase_secret_key:
        raise ValueError("SUPABASE_SECRET_KEY is not configured")

    return create_client(settings.supabase_url, settings.supabase_secret_key)


def get_supabase() -> Generator[Client, None, None]:
    """FastAPI dependency that yields the Supabase client.

    Yields:
        Supabase client instance for use in route handlers.

    Example:
        @router.get("/items")
        def list_items(supabase: Client = Depends(get_supabase)):
            result = supabase.table("items").select("*").execute()
            return result.data
    """
    client = get_supabase_client()
    try:
        yield client
    finally:
        # Supabase client doesn't require explicit cleanup
        pass
