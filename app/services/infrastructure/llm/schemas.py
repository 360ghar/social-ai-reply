"""Pydantic schemas for structured LLM outputs.

These replace raw dict returns from LLM calls with typed, validated models.
Pydantic AI uses these as output_type on Agent definitions, providing automatic
validation, re-prompting on failure, and type-safe downstream usage.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BrandAnalysisResult(BaseModel):
    """Structured output from the brand analysis agent."""

    brand_name: str = Field(min_length=1, description="Extracted brand or company name")
    summary: str = Field(min_length=10, description="Concise brand summary")
    product_summary: str = Field(min_length=10, description="Core business problem the company solves")
    target_audience: str = Field(min_length=5, description="Domain-specific target audience")
    call_to_action: str = Field(min_length=5, description="Appropriate CTA for the brand")
    voice_notes: str = Field(default="Helpful, grounded, and specific.", description="Brand voice guidelines")
    business_domain: str = Field(
        default="",
        description=(
            "Short label identifying the core industry vertical "
            "(e.g. 'real estate', 'healthcare', 'fintech', 'saas')"
        ),
    )


class ReplyDraftResult(BaseModel):
    """Structured output from the reply generator agent."""

    content: str = Field(min_length=30, description="The Reddit reply text")
    rationale: str = Field(description="Why this reply is appropriate for this opportunity")


class PostDraftResult(BaseModel):
    """Structured output from the post generator agent."""

    title: str = Field(min_length=5, max_length=300, description="Reddit post title")
    body: str = Field(min_length=20, description="Reddit post body text")
    rationale: str = Field(description="Why this post is a good fit for the target subreddit")
