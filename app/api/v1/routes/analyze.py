"""Streaming analysis endpoint — zero-input URL enrichment via SSE.

POST /v1/analyze/stream?url=https://example.com

Streams JSON events back to the client as each enrichment step completes:
  {"type": "log",      "msg": "...", "level": "info|success|warn"}
  {"type": "data",     "key": "company_name", "value": "..."}
  {"type": "section",  "label": "Brand Intelligence"}
  {"type": "complete", "company": {...}, "keywords": [...], "competitors": [...]}
  {"type": "error",    "msg": "..."}

The client renders these as a terminal stream, then hydrates the workflow
steps automatically when "complete" arrives.
"""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

if TYPE_CHECKING:
    from supabase import Client

from app.api.v1.deps import get_current_user, get_current_workspace
from app.db.supabase_client import get_supabase
from app.db.tables.company import get_company_by_workspace, update_company
from app.services.product.brand_brain import BrandBrain

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/analyze", tags=["analyze"])


def _event(data: dict[str, Any]) -> str:
    """Format a dict as an SSE event line."""
    return f"data: {json.dumps(data)}\n\n"


def _log(msg: str, level: str = "info") -> str:
    return _event({"type": "log", "msg": msg, "level": level})


def _data(key: str, value: Any) -> str:
    return _event({"type": "data", "key": key, "value": value})


def _section(label: str) -> str:
    return _event({"type": "section", "label": label})


async def _analysis_generator(
    url: str,
    workspace: dict,
    supabase: "Client",
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE events as enrichment progresses."""
    import asyncio

    yield _log(f"Starting analysis for {url}…")
    yield _log("Fetching company profile from database…")

    # Step 0: Load or create company profile
    try:
        company_profile = get_company_by_workspace(supabase, workspace["id"])
    except Exception:
        company_profile = None

    if not company_profile:
        yield _log("No company profile found — creating one from URL…", "warn")
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url if url.startswith("http") else f"https://{url}")
            domain = parsed.netloc.replace("www.", "")
            name_guess = domain.split(".")[0].title()

            result = supabase.table("company_profiles").insert({
                "workspace_id": workspace["id"],
                "name": name_guess,
                "website_url": url,
                "is_active": True,
                "language": "en",
                "features": "",
                "benefits": "",
                "pain_points": "",
                "competitors": "",
            }).execute()
            company_profile = result.data[0] if result.data else None
        except Exception as exc:
            yield _log(f"Could not create company profile: {exc}", "warn")

    if not company_profile:
        yield _event({"type": "error", "msg": "No company profile available. Create one first in Company Setup."})
        return

    company_id = company_profile.get("id")
    yield _log(f"Found profile: {company_profile.get('name', 'Unnamed')} (ID {company_id})")
    yield _data("company_id", company_id)

    # Step 1: Crawl and analyse website
    yield _section("Website Analysis")
    yield _log(f"Crawling {url}…")

    brain = BrandBrain()

    # Run synchronous BrandBrain in a thread so we don't block event loop
    loop = asyncio.get_event_loop()

    try:
        yield _log("Fetching homepage HTML…")
        enriched = await loop.run_in_executor(
            None,
            lambda: brain.analyze_website(url, dict(company_profile), supabase),
        )
        yield _log("Homepage parsed ✓", "success")
    except Exception as exc:
        yield _log(f"Website crawl failed: {exc}", "warn")
        enriched = company_profile

    # Stream key extracted data as it becomes available
    yield _section("Extracted Intelligence")

    company_name = enriched.get("name") or company_profile.get("name") or ""
    if company_name:
        yield _log(f"Company: {company_name}", "success")
        yield _data("company_name", company_name)

    summary = enriched.get("extracted_summary") or enriched.get("description") or ""
    if summary:
        preview = summary[:120] + ("…" if len(summary) > 120 else "")
        yield _log(f"Summary: {preview}")
        yield _data("summary", summary)

    audience = enriched.get("target_audience", "")
    if audience:
        yield _log(f"Audience: {audience}")
        yield _data("target_audience", audience)

    brand_voice = enriched.get("brand_voice", "")
    if brand_voice:
        yield _log(f"Brand voice: {brand_voice}")
        yield _data("brand_voice", brand_voice)

    # Competitors
    yield _section("Competitor Discovery")
    raw_competitors = enriched.get("competitors") or enriched.get("extracted_competitors") or ""
    competitor_list: list[str] = []
    if isinstance(raw_competitors, str):
        competitor_list = [c.strip() for c in raw_competitors.split(",") if c.strip()]
    elif isinstance(raw_competitors, list):
        competitor_list = raw_competitors

    if competitor_list:
        for comp in competitor_list[:8]:
            yield _log(f"  Found competitor: {comp}", "success")
        yield _data("competitors", competitor_list)
    else:
        yield _log("No competitors detected on site — DDG search already ran during crawl", "warn")

    # Step 2: Generate keywords if none exist
    yield _section("Keyword Generation")
    try:
        from app.services.product.discovery import get_project_search_keywords
        from app.db.tables.projects import get_projects_for_workspace

        projects = get_projects_for_workspace(supabase, workspace["id"])
        project = projects[0] if projects else None

        if project:
            existing_kws = get_project_search_keywords(supabase, project, limit=5)
            if not existing_kws:
                yield _log("No keywords yet — generating from brand profile…")
                from app.services.product.copilot import suggest_personas, generate_keywords
                from app.db.tables.discovery import list_personas_for_project

                # Build brand dict for keyword gen
                brand_dict = {
                    "brand_name": enriched.get("name", ""),
                    "summary": enriched.get("extracted_summary", ""),
                    "product_summary": enriched.get("description", ""),
                    "target_audience": enriched.get("target_audience", ""),
                    "business_domain": enriched.get("category", ""),
                    "geography": enriched.get("geography", ""),
                }

                personas_list = list_personas_for_project(supabase, project["id"])
                persona_dicts = [
                    {
                        "name": p.get("name", ""),
                        "role": p.get("role", ""),
                        "summary": p.get("summary", ""),
                        "pain_points": p.get("pain_points", []),
                    }
                    for p in (personas_list or [])
                ]

                generated_kws = await loop.run_in_executor(
                    None,
                    lambda: generate_keywords(brand_dict, persona_dicts, count=20),
                )

                # Persist keywords
                from app.db.tables.discovery import create_discovery_keyword
                saved = 0
                for kw_obj in generated_kws[:20]:
                    try:
                        kw_str = kw_obj.keyword if hasattr(kw_obj, "keyword") else str(kw_obj)
                        priority = kw_obj.priority_score if hasattr(kw_obj, "priority_score") else 5
                        create_discovery_keyword(supabase, {
                            "project_id": project["id"],
                            "keyword": kw_str,
                            "rationale": getattr(kw_obj, "rationale", "AI generated"),
                            "priority_score": priority,
                            "source": "ai",
                            "is_active": True,
                        })
                        saved += 1
                        yield _log(f"  Keyword: {kw_str}")
                    except Exception:
                        pass

                yield _log(f"Generated {saved} keywords ✓", "success")
                yield _data("keywords_count", saved)
            else:
                yield _log(f"Using {len(existing_kws)} existing keywords")
                yield _data("keywords_count", len(existing_kws))
    except Exception as exc:
        yield _log(f"Keyword generation skipped: {exc}", "warn")

    # Step 3: Personas
    yield _section("Persona Generation")
    try:
        if project:
            from app.db.tables.discovery import list_personas_for_project
            existing_personas = list_personas_for_project(supabase, project["id"])
            if not existing_personas:
                yield _log("No personas yet — generating from brand profile…")
                from app.services.product.copilot import suggest_personas as _sp
                from app.db.tables.discovery import create_persona

                persona_data = await loop.run_in_executor(
                    None,
                    lambda: _sp(brand_dict, count=3),
                )
                for pd in persona_data[:3]:
                    try:
                        create_persona(supabase, {
                            "project_id": project["id"],
                            "name": pd.get("name", ""),
                            "role": pd.get("role", ""),
                            "summary": pd.get("summary", ""),
                            "pain_points": pd.get("pain_points", []),
                            "goals": pd.get("goals", []),
                            "triggers": pd.get("triggers", []),
                            "source": "ai",
                            "is_active": True,
                        })
                        yield _log(f"  Persona: {pd.get('name', '?')} — {pd.get('role', '')}", "success")
                    except Exception:
                        pass
                yield _data("personas_count", len(persona_data))
            else:
                yield _log(f"Using {len(existing_personas)} existing personas")
                yield _data("personas_count", len(existing_personas))
    except Exception as exc:
        yield _log(f"Persona generation skipped: {exc}", "warn")

    # Done
    yield _section("Complete")
    yield _log("Analysis complete — workflow steps auto-populated ✓", "success")
    yield _event({
        "type": "complete",
        "company": {
            "id": company_id,
            "name": enriched.get("name", ""),
            "website_url": url,
            "summary": enriched.get("extracted_summary", ""),
            "target_audience": enriched.get("target_audience", ""),
            "brand_voice": enriched.get("brand_voice", ""),
            "competitors": competitor_list,
        },
    })


@router.post("/stream")
async def analyze_stream(
    url: str = Query(..., description="Company website URL to analyze"),
    current_user: dict = Depends(get_current_user),
    workspace: dict = Depends(get_current_workspace),
    supabase: "Client" = Depends(get_supabase),
) -> StreamingResponse:
    """Stream brand enrichment events as SSE while analyzing a URL.

    The client should consume this as an EventSource (or via fetch with
    ReadableStream) and render each event in the terminal UI.
    """
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="url is required")

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    return StreamingResponse(
        _analysis_generator(url, workspace, supabase),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )
