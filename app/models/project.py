"""Pydantic models for project-related tables."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ProjectStatus(StrEnum):
    """Status values for project."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Project(BaseModel):
    """Model for projects table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    name: str = Field(min_length=1, max_length=255)
    slug: str
    description: str | None = Field(default=None, max_length=4000)
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


class BrandProfile(BaseModel):
    """Model for brand_profiles table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    business_name: str = Field(min_length=1, max_length=255)
    domain: str | None = None
    target_audience: str | None = None
    value_proposition: str | None = None
    brand_voice: str | None = None
    website_content: str | None = None
    analyzed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PromptTemplate(BaseModel):
    """Model for prompt_templates table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    prompt_type: str
    template: str
    is_default: bool
    created_at: datetime
    updated_at: datetime
