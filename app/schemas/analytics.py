from pydantic import BaseModel, Field


class HandleMetric(BaseModel):
    instagram_user_id: int
    username: str
    metric_count: int
    distinct_profiles: int


class QueryResponse(BaseModel):
    query_name: str
    threshold: int = Field(default=0, ge=0)
    results: list[HandleMetric]
    csv_path: str | None = None
