from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CustomScraperCreateRequest(BaseModel):
    """Payload for creating or updating a custom scraper."""
    platform: str = Field(pattern="^(instagram|twitter|linkedin|reddit)$", description="Target platform")
    api_key: str | None = Field(default=None, description="API key for the custom scraper")
    api_host: str = Field(min_length=1, description="Host of the API, e.g., instagram-scraper2.p.rapidapi.com")
    search_endpoint: str = Field(min_length=1, description="Endpoint to search for keywords")
    search_param_name: str = Field(min_length=1, description="Query parameter name for the keyword")
    comments_endpoint: str | None = Field(default=None, description="Optional endpoint to fetch comments")
    comments_param_name: str | None = Field(default=None, description="Optional parameter for the post ID")
    items_json_path: str = Field(min_length=1, description="Dot-notation path to extract items array, e.g., 'data.items'")
    is_active: bool = Field(default=True)


class CustomScraperResponse(BaseModel):
    """Response model for a custom scraper."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    platform: str
    api_host: str
    search_endpoint: str
    search_param_name: str
    comments_endpoint: str | None
    comments_param_name: str | None
    items_json_path: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # We do NOT return the api_key for security reasons, unless explicitly needed.


class ScraperTestRequest(BaseModel):
    """Payload for testing a scraper configuration."""
    api_host: str = Field(min_length=1)
    api_key: str | None = Field(default=None)
    search_endpoint: str = Field(min_length=1)
    search_param_name: str = Field(min_length=1)
    items_json_path: str = Field(default="")
    test_query: str = Field(default="test", max_length=100)


class ScraperTestResponse(BaseModel):
    """Response from testing a scraper configuration."""
    success: bool
    status_code: int = 0
    error: str | None = None
    sample_keys: list[str] = Field(default_factory=list, description="Top-level keys in the response")
    suggested_json_path: str | None = Field(default=None, description="Auto-detected path to the items array")
    items_found: int = 0
    warnings: list[str] = Field(default_factory=list)

