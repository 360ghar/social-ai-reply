"""Copilot module for AI-powered brand analysis and content generation."""

from app.services.product.copilot._facade import ProductCopilot
from app.services.product.copilot.analyzer import (
    WebsiteAnalysis,
    WebsiteAnalyzer,
    analyze_website,
)
from app.services.product.copilot.inference import (
    infer_audience,
    infer_business_domain,
    infer_cta,
)
from app.services.product.copilot.keyword import GeneratedKeyword, generate_keywords
from app.services.product.copilot.llm_client import LLMClient
from app.services.product.copilot.persona import suggest_personas
from app.services.product.copilot.post import generate_post
from app.services.product.copilot.reply import generate_reply

__all__ = [
    # Facade (backward compatibility)
    "ProductCopilot",
    # Analyzer
    "WebsiteAnalysis",
    "WebsiteAnalyzer",
    "analyze_website",
    # Persona
    "suggest_personas",
    # Keyword
    "GeneratedKeyword",
    "generate_keywords",
    # Reply
    "generate_reply",
    # Post
    "generate_post",
    # Inference
    "infer_audience",
    "infer_cta",
    "infer_business_domain",
    # LLM Client
    "LLMClient",
]
