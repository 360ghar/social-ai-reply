import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

from app.db.tables.company import get_company_by_url
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

    # Load or create company profile based on the URL
    try:
        from app.db.tables.company import get_company_by_url
        company_profile = get_company_by_url(supabase, workspace["id"], url)
    except Exception as exc:
        yield _log(f"Error fetching company profile: {exc}", "warn")
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
        from app.db.tables.discovery import list_personas_for_project
        from app.services.product.discovery import get_project_search_keywords
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
        kws_list = [
            {"keyword": kw.keyword if hasattr(kw, "keyword") else str(kw), "type": getattr(kw, "category", "core"), "priority": getattr(kw, "priority_score", 5)}
            for kw in generated
        ]
        yield _log(f"Generated {len(kws_list)} keywords.", "success")
        yield _data("keywords_count", len(kws_list))
    else:
        kws_list = kws_db

    # 2. Parallel Scraping
    yield _section("Parallel Free Source Discovery")
    from app.scrapers.free_sources import find_competitors_ddg
    from app.services.product.platform_scanner import _async_platform_scan

    def _kw_str(k):
        if isinstance(k, dict):
            v = k.get("keyword", "")
            return v.keyword if hasattr(v, "keyword") else str(v)
        return k.keyword if hasattr(k, "keyword") else str(k)
    keywords_flat = [_kw_str(k) for k in kws_list if _kw_str(k)] if kws_list else [company_name]
    yield _log(f"Scraping using {len(keywords_flat)} keywords across platforms…")

    import concurrent.futures
    all_posts = []

    # 2a. Determine Reddit subreddits
    yield _log("Determining relevant subreddits…")
    from app.services.infrastructure.llm.service import LLMService
    llm = LLMService()
    # Build a smarter domain-aware fallback in case LLM fails or returns garbage
    def _domain_fallback_subreddits(company_nm: str, description: str) -> list[str]:
        """Return contextually appropriate fallback subreddits based on company domain."""
        desc_lower = (description or "").lower()
        name_lower = (company_nm or "").lower()
        combined = f"{name_lower} {desc_lower}"

        # Map domain signals → subreddits
        domain_map = [
            (["ecommerce", "shopping", "india", "flipkart", "meesho", "myntra", "delivery", "grocery"],
             ["india", "IndiaShipping", "OnlineShopping", "IndianFinance", "InstacartShoppers"]),
            (["saas", "software", "b2b", "api", "developer", "devtool"],
             ["SaaS", "startups", "webdev", "programming"]),
            (["health", "fitness", "wellness", "medical"],
             ["health", "fitness", "nutrition", "loseit"]),
            (["finance", "fintech", "payment", "banking", "invest"],
             ["personalfinance", "investing", "FinancialPlanning", "IndiaInvestments"]),
            (["real estate", "property", "mortgage", "housing"],
             ["realestate", "RealEstateInvesting", "FirstTimeHomeBuyer"]),
            (["education", "edtech", "learning", "course", "tutor"],
             ["education", "learnprogramming", "OnlineLearning"]),
            (["food", "restaurant", "delivery", "recipe"],
             ["food", "recipes", "mealprep", "MealPrepSunday"]),
        ]
        for signals, subs in domain_map:
            if any(sig in combined for sig in signals):
                return subs[:3]
        # Generic fallback
        return ["startups", "smallbusiness", "Entrepreneur"]

    fallback_subs = _domain_fallback_subreddits(company_name, enriched.get("description", ""))

    subreddit_prompt = (
        f"You are a Reddit community expert. Suggest exactly 3 active subreddits where people would "
        f"discuss or ask about a product like '{company_name}' which does: '{enriched.get('description', '')}'. "
        f"Return ONLY a comma-separated list of subreddit names WITHOUT r/ prefix and WITHOUT any explanation. "
        f"Example format: india,OnlineShopping,IndiaFinance"
    )
    try:
        subreddits_response = await loop.run_in_executor(None, lambda: llm.generate(subreddit_prompt))
        # Clean up the response — strip markdown, backticks, bullets etc.
        clean = subreddits_response.strip().strip("`").replace("\n", ",").replace(";", ",")
        # Remove any "r/" prefix the LLM may have added
        subreddits = [s.strip().lstrip("r/").strip() for s in clean.split(",") if s.strip()]
        # Validate: each name must look like a real subreddit (no spaces, no long sentences)
        subreddits = [s for s in subreddits if s and " " not in s and len(s) < 40][:3]
        if len(subreddits) < 2:
            subreddits = fallback_subs
    except Exception:
        subreddits = fallback_subs
    yield _log(f"Selected subreddits: {', '.join(subreddits)}", "info")

    # Run all platforms (including new free native scrapers) via PlatformRouter asynchronously
    router_platforms = ["twitter", "linkedin", "instagram", "hackernews", "github", "reddit", "indiehackers"]
    try:
        router_results = await _async_platform_scan(
            platforms=router_platforms,
            search_keywords=keywords_flat[:3],
            limit_per_platform=10,
            subreddits=subreddits,
            workspace_id=workspace["id"],
            db=supabase
        )
        if router_results:
            yield _log(f"Found {len(router_results)} posts across platforms", "success")
            all_posts.extend(router_results)
        else:
            yield _log("Platform scan returned 0 posts — keywords or subreddits may need tuning", "warn")
    except Exception as scan_err:
        yield _log(f"Platform scan error (non-fatal): {scan_err}", "warn")
        router_results = []

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
    from app.services.product.scanner import CandidatePost

    engine = RelevanceEngine()
    engine_brand = {
        "name": company_name,
        "brand_name": company_name,
        "description": enriched.get("extracted_summary") or enriched.get("description", ""),
        "product_summary": enriched.get("extracted_summary", ""),
        "target_audience": enriched.get("target_audience", ""),
        "category": enriched.get("category", ""),
        "pain_points": [],   # populated from personas if available
        "competitors": competitor_list,
    }
    # Merge persona pain points for better relevance scoring
    if personas_list:
        all_pain_points = []
        for p in personas_list[:3]:
            pts = p.get("pain_points", []) if isinstance(p, dict) else []
            if isinstance(pts, list):
                all_pain_points.extend(str(pt) for pt in pts if pt)
        engine_brand["pain_points"] = list(dict.fromkeys(all_pain_points))[:15]

    scored_opps = []
    if not all_posts:
        yield _log("No posts found to score — try broader keywords or different subreddits", "warn")
        yield _log("Tip: Reddit blocks direct API calls from server IPs. Use the manual Subreddits page to add communities, then run a scan from the Discovery page.", "info")
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

                # Build keyword list for scoring — use all flat keywords as dicts
                engine_kws = [{"keyword": kw, "type": "core", "weight": 1.0} for kw in keywords_flat[:10]]
                if not engine_kws:
                    engine_kws = [{"keyword": company_name, "type": "core", "weight": 1.0}]
                result = await loop.run_in_executor(
                    None,
                    lambda c=candidate, kws=engine_kws: engine.score(c, engine_brand, kws)
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
