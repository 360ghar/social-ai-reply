import asyncio
import json
from typing import Any, AsyncGenerator

from app.db.tables.company import get_company_by_workspace
from app.db.tables.projects import list_projects_for_workspace
from app.services.product.brand_brain import BrandBrain
from app.services.product.docs import generate_markdown_report


def _event(data: dict[str, Any]) -> str:
    """Format a dict as an SSE event line."""
    return f"data: {json.dumps(data)}\n\n"


def _log(msg: str, level: str = "info") -> str:
    return _event({"type": "log", "msg": msg, "level": level})


def _data(key: str, value: Any) -> str:
    return _event({"type": "data", "key": key, "value": value})


def _section(label: str) -> str:
    return _event({"type": "section", "label": label})


async def run_full_pipeline_stream(url: str, workspace: dict, supabase: Any) -> AsyncGenerator[str, None]:
    """
    Zero-Input Master Pipeline.
    Runs enrichment, scraping, relevance scoring, and document generation.
    """
    yield _log(f"Starting master pipeline for {url}…")
    yield _log("Step 1: Auto-Enrichment via URL")

    # Load or create company profile
    try:
        company_profile = get_company_by_workspace(supabase, workspace["id"])
    except Exception:
        company_profile = None

    if not company_profile:
        yield _log("Creating new company profile from URL…")
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

    if not company_profile:
        yield _event({"type": "error", "msg": "Failed to create company profile."})
        return

    company_id = company_profile.get("id")
    yield _data("company_id", company_id)

    # 1. Enrich (BrandBrain)
    yield _section("Crawling Website")
    brain = BrandBrain()
    loop = asyncio.get_running_loop()
    try:
        enriched = await loop.run_in_executor(
            None,
            lambda: brain.analyze_website(url, dict(company_profile), supabase),
        )
        yield _log("Website parsed and intelligence extracted ✓", "success")
    except Exception as exc:
        yield _log(f"Website crawl failed: {exc}", "warn")
        enriched = company_profile

    company_name = enriched.get("name") or company_profile.get("name") or ""
    yield _data("company_name", company_name)
    yield _log(f"Identified Brand: {company_name}")

    # Competitors
    raw_competitors = enriched.get("competitors") or enriched.get("extracted_competitors") or ""
    competitor_list = []
    if isinstance(raw_competitors, str):
        competitor_list = [c.strip() for c in raw_competitors.split(",") if c.strip()]
    elif isinstance(raw_competitors, list):
        competitor_list = raw_competitors

    if competitor_list:
        for comp in competitor_list[:3]:
            yield _log(f"Found competitor: {comp}", "success")
            
    # Keywords & Personas
    yield _section("Generating Personas & Keywords")
    projects = list_projects_for_workspace(supabase, workspace["id"])
    project = projects[0] if projects else None

    kws_list = []
    personas_list = []

    if project:
        from app.services.product.discovery import get_project_search_keywords
        from app.db.tables.discovery import list_personas_for_project
        personas_list = list_personas_for_project(supabase, project["id"]) or []
        kws_db = get_project_search_keywords(supabase, project, limit=10)
    else:
        personas_list = []
        kws_db = []

    if not personas_list:
        yield _log("Generating target personas…")
        from app.services.product.copilot import suggest_personas
        personas_list = await loop.run_in_executor(
            None,
            lambda: suggest_personas({
                "brand_name": enriched.get("name", ""),
                "product_summary": enriched.get("description", ""),
                "target_audience": enriched.get("target_audience", ""),
            }),
        )
        yield _log(f"Generated {len(personas_list)} personas.", "success")
        yield _data("personas_count", len(personas_list))
    
    if not kws_db:
        yield _log("Generating search keywords…")
        from app.services.product.copilot import generate_keywords
        generated = await loop.run_in_executor(
            None,
            lambda: generate_keywords({
                "brand_name": enriched.get("name", ""),
                "summary": enriched.get("extracted_summary", ""),
                "product_summary": enriched.get("description", ""),
            }, personas_list),
        )
        kws_list = [{"keyword": kw, "type": "core"} for kw in generated]
        yield _log(f"Generated {len(kws_list)} keywords.", "success")
        yield _data("keywords_count", len(kws_list))
    else:
        kws_list = kws_db

    # 2. Parallel Scraping
    yield _section("Parallel Free Source Discovery")
    from app.scrapers.free_sources import scrape_hackernews, scrape_github, scrape_reddit_json, find_competitors_ddg
    from app.services.product.platform_scanner import _async_platform_scan

    keywords_flat = [(k["keyword"] if isinstance(k, dict) else k) for k in kws_list] if kws_list else [company_name]
    yield _log(f"Scraping using {len(keywords_flat)} keywords across platforms…")

    import concurrent.futures
    all_posts = []
    
    # 2a. Determine Reddit subreddits
    yield _log("Determining relevant subreddits…")
    from app.services.infrastructure.llm.service import LLMService
    llm = LLMService()
    subreddit_prompt = f"Suggest 3 popular, active subreddits where people would discuss a product like '{company_name}' which does '{enriched.get('description', '')}'. Return ONLY a comma-separated list of subreddit names without the 'r/'. Example: SaaS,EntrepreneurRideAlong,marketing"
    try:
        subreddits_response = await loop.run_in_executor(None, lambda: llm.generate(subreddit_prompt))
        subreddits = [s.strip() for s in subreddits_response.split(",") if s.strip()][:3]
        if not subreddits:
            subreddits = ["SaaS", "EntrepreneurRideAlong", "marketing"]
    except Exception:
        subreddits = ["SaaS", "EntrepreneurRideAlong", "marketing"]
    yield _log(f"Selected subreddits: {', '.join(subreddits)}", "info")
    
    # Run all platforms (including new free native scrapers) via PlatformRouter asynchronously
    router_platforms = ["twitter", "linkedin", "instagram", "hackernews", "github", "reddit", "indiehackers"]
    router_results = await _async_platform_scan(
        platforms=router_platforms,
        search_keywords=keywords_flat[:3],
        limit_per_platform=10,
        subreddits=subreddits,
        workspace_id=workspace["id"],
        db=supabase
    )
    if router_results:
        yield _log(f"Found {len(router_results)} posts via alternative scrapers", "success")
        all_posts.extend(router_results)
    
    # Still use DuckDuckGo for competitor discovery
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        try:
            res = await loop.run_in_executor(executor, find_competitors_ddg, company_name)
            if res:
                yield _log(f"Found {len(res)} alternative competitors on DDG", "success")
                for c in res:
                    if c not in competitor_list:
                        competitor_list.append(c)
        except Exception as e:
            yield _log(f"Error scraping DuckDuckGo: {e}", "warn")

    # 3. AI Scoring
    yield _section("AI Relevance Scoring")
    from app.services.product.relevance_v2 import RelevanceEngine
    from app.services.product.scanner import CandidatePost, _result_payload
    from app.db.tables.discovery import create_opportunity
    
    engine = RelevanceEngine()
    engine_brand = {
        "brand_name": company_name,
        "product_summary": enriched.get("extracted_summary", ""),
        "competitors": competitor_list,
    }
    
    scored_opps = []
    if not all_posts:
        yield _log("No posts found to score.", "warn")
    else:
        yield _log(f"Scoring {len(all_posts)} posts against brand profile…")
        for i, fp in enumerate(all_posts[:20]): # Limit to top 20 to save time in UI stream
            try:
                # Handle both FreePost (has .score, .source) and UnifiedPost (has .upvotes, only .platform)
                is_free_post = hasattr(fp, "source")
                upvotes = getattr(fp, "score", getattr(fp, "upvotes", 0))
                source_name = getattr(fp, "subreddit", None) or getattr(fp, "source", fp.platform)
                
                candidate = CandidatePost(
                    title=fp.title or "",
                    body=fp.body or "",
                    platform=fp.platform,
                    source_name=source_name,
                    upvotes=upvotes,
                    comments_count=fp.comments_count,
                    created_at=fp.created_at,
                    author=fp.author,
                    post_url=fp.url,
                )
                
                # Assign a pseudo keyword for scoring
                engine_kw = {"keyword": keywords_flat[0] if keywords_flat else "", "type": "core"}
                result = await loop.run_in_executor(
                    None,
                    lambda: engine.score(candidate, engine_brand, [engine_kw])
                )
                
                if result.relevance_score >= 50:
                    yield _log(f"High-value opportunity on {fp.platform} (Score: {result.relevance_score})", "success")
                    # Optionally save to DB here...
                    opp = {
                        "platform": fp.platform,
                        "title": fp.title,
                        "body": fp.body,
                        "post_url": fp.url,
                        "score": result.relevance_score,
                    }
                    scored_opps.append(opp)
            except Exception as e:
                yield _log(f"Error scoring post: {e}", "warn")

    # 4. Generate Document
    yield _section("Generating Final Report")
    yield _log("Compiling living document…")
    
    report_md = generate_markdown_report(
        company=enriched,
        keywords=kws_list,
        personas=personas_list,
        opportunities=scored_opps,
    )
    
    yield _data("report", report_md)
    yield _log("Report ready.", "success")
    
    yield _event({
        "type": "complete",
        "company": enriched,
        "keywords": kws_list,
        "competitors": competitor_list,
        "opportunities_count": len(scored_opps),
        "report": report_md
    })
