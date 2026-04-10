"""Background task to run the auto-pipeline from website URL to sales package."""

import logging
import traceback
from datetime import UTC, datetime

from app.db.tables.analytics import get_auto_pipeline_by_id, update_auto_pipeline
from app.db.tables.content import create_reply_draft
from app.db.tables.discovery import (
    list_monitored_subreddits_for_project,
    list_opportunities_for_project,
    list_personas_for_project,
    update_opportunity,
)
from app.db.tables.projects import (
    create_brand_profile,
    get_brand_profile_by_project,
    get_project_by_id,
    list_prompt_templates_for_project,
    update_brand_profile,
)
from app.db.tables.system import create_notification
from app.schemas.v1.discovery import ScanRequest
from app.services.product.copilot import ProductCopilot
from app.services.product.discovery import discover_and_store_subreddits
from app.services.product.scanner import revalidate_opportunity, run_scan
from app.services.product.scoring import MIN_RELEVANT_OPPORTUNITY_SCORE

log = logging.getLogger("redditflow.pipeline")
TARGET_PIPELINE_SUBREDDITS = 10


def run_auto_pipeline_background(
    pipeline_id: str,
    website_url: str,
    project_id: int,
    workspace_id: int,
    user_id: int,
):
    from app.db.supabase_client import get_supabase_client
    db = get_supabase_client()

    log.info("=== AUTO-PIPELINE START === id=%s url=%s project=%s", pipeline_id, website_url, project_id)

    try:
        pipeline = get_auto_pipeline_by_id(db, pipeline_id)
        if not pipeline:
            log.error("Pipeline %s not found in DB — aborting.", pipeline_id)
            return

        proj = get_project_by_id(db, project_id)
        if not proj:
            log.error("Project %s not found in DB — aborting.", project_id)
            return

        copilot = ProductCopilot()
        log.info("Step 1/7: Analyzing website %s", website_url)

        # ── Step 1: Analyze Website (0→15%) ─────────────────────
        update_auto_pipeline(db, pipeline_id, {
            "status": "analyzing",
            "progress": 5,
            "current_step": "Analyzing website content...",
        })

        try:
            website_analysis = copilot.analyze_website(website_url)
            log.info("Website analysis OK — brand=%s summary_len=%d",
                     website_analysis.brand_name, len(website_analysis.summary or ""))
        except Exception as e:
            log.error("Website analysis FAILED: %s\n%s", e, traceback.format_exc())
            raise

        update_auto_pipeline(db, pipeline_id, {"brand_summary": website_analysis.summary, "progress": 15})

        brand = get_brand_profile_by_project(db, project_id)
        if brand:
            update_brand_profile(db, brand["id"], {
                "brand_name": website_analysis.brand_name,
                "summary": website_analysis.summary,
                "product_summary": website_analysis.product_summary,
                "target_audience": website_analysis.target_audience,
                "call_to_action": website_analysis.call_to_action,
                "voice_notes": website_analysis.voice_notes,
                "business_domain": website_analysis.business_domain,
            })
            log.info("Updated existing BrandProfile id=%s", brand["id"])
        else:
            create_brand_profile(db, {
                "project_id": project_id,
                "brand_name": website_analysis.brand_name,
                "website_url": website_url,
                "summary": website_analysis.summary,
                "product_summary": website_analysis.product_summary,
                "target_audience": website_analysis.target_audience,
                "call_to_action": website_analysis.call_to_action,
                "voice_notes": website_analysis.voice_notes,
                "business_domain": website_analysis.business_domain,
            })
            log.info("Created new BrandProfile for project %s", project_id)

        # ── Step 2: Generate Personas (15→30%) ──────────────────
        log.info("Step 2/7: Generating personas")
        update_auto_pipeline(db, pipeline_id, {
            "status": "generating_personas",
            "progress": 20,
            "current_step": "Generating target personas...",
        })

        try:
            personas_data = copilot.suggest_personas(
                type("BrandProfile", (), {
                    "brand_name": website_analysis.brand_name,
                    "summary": website_analysis.summary,
                    "product_summary": website_analysis.product_summary,
                    "target_audience": website_analysis.target_audience,
                    "call_to_action": website_analysis.call_to_action,
                    "voice_notes": website_analysis.voice_notes,
                    "business_domain": website_analysis.business_domain,
                })(),
                count=4,
            )
            log.info("Generated %d personas", len(personas_data))
        except Exception as e:
            log.error("Persona generation FAILED: %s\n%s", e, traceback.format_exc())
            raise

        from app.db.tables.discovery import create_persona
        for p_data in personas_data:
            create_persona(db, {
                "project_id": project_id,
                "name": p_data["name"],
                "role": p_data.get("role"),
                "summary": p_data["summary"],
                "pain_points": p_data.get("pain_points", []),
                "goals": p_data.get("goals", []),
                "triggers": p_data.get("triggers", []),
                "preferred_subreddits": p_data.get("preferred_subreddits", []),
                "source": "generated",
            })
        update_auto_pipeline(db, pipeline_id, {"personas_generated": len(personas_data), "progress": 30})

        # ── Step 3: Discover Keywords (30→45%) ──────────────────
        log.info("Step 3/7: Discovering keywords")
        update_auto_pipeline(db, pipeline_id, {
            "status": "discovering_keywords",
            "progress": 35,
            "current_step": "Discovering relevant keywords...",
        })

        personas_list = list_personas_for_project(db, project_id)
        try:
            keywords_data = copilot.generate_keywords(
                type("BrandProfile", (), {
                    "brand_name": website_analysis.brand_name,
                    "summary": website_analysis.summary,
                    "product_summary": website_analysis.product_summary,
                    "target_audience": website_analysis.target_audience,
                    "call_to_action": website_analysis.call_to_action,
                    "voice_notes": website_analysis.voice_notes,
                    "business_domain": website_analysis.business_domain,
                })(),
                personas_list,
                count=15,
            )
            log.info("Generated %d keywords", len(keywords_data))
        except Exception as e:
            log.error("Keyword generation FAILED: %s\n%s", e, traceback.format_exc())
            raise

        from app.db.tables.discovery import create_discovery_keyword, list_discovery_keywords_for_project
        existing_kw = {row["keyword"] for row in list_discovery_keywords_for_project(db, project_id)}
        new_kw_count = 0
        for k_data in keywords_data:
            if k_data["keyword"] in existing_kw:
                log.info("Keyword '%s' already exists — skipping", k_data["keyword"])
                continue
            create_discovery_keyword(db, {
                "project_id": project_id,
                "keyword": k_data["keyword"],
                "rationale": k_data["rationale"],
                "priority_score": k_data["priority_score"],
                "source": "generated",
            })
            existing_kw.add(k_data["keyword"])
            new_kw_count += 1
        update_auto_pipeline(db, pipeline_id, {"keywords_generated": len(keywords_data), "progress": 45})
        log.info("Inserted %d new keywords (%d already existed)", new_kw_count, len(keywords_data) - new_kw_count)

        # ── Step 4: Discover Subreddits (45→60%) ────────────────
        log.info("Step 4/7: Discovering subreddits")
        update_auto_pipeline(db, pipeline_id, {
            "status": "finding_subreddits",
            "progress": 50,
            "current_step": "Discovering relevant subreddits...",
        })

        existing_sub_count = len(list_monitored_subreddits_for_project(db, project_id))
        subreddits_to_discover = max(TARGET_PIPELINE_SUBREDDITS - existing_sub_count, 0)
        try:
            if subreddits_to_discover > 0:
                created_subreddits = discover_and_store_subreddits(
                    db,
                    proj,
                    max_subreddits=subreddits_to_discover,
                )
                discovered_subreddits = [row["name"] for row in created_subreddits]
            else:
                discovered_subreddits = []
                log.info(
                    "Skipping subreddit discovery because project %s already has %d active subreddits",
                    project_id,
                    existing_sub_count,
                )
        except Exception as e:
            log.error("Subreddit discovery FAILED: %s\n%s", e, traceback.format_exc())
            discovered_subreddits = []

        update_auto_pipeline(db, pipeline_id, {
            "subreddits_found": existing_sub_count + len(discovered_subreddits),
            "progress": 60,
        })
        log.info("Discovered %d new subreddits (%d already existed)", len(discovered_subreddits), existing_sub_count)

        # ── Step 5: Scan for Opportunities (60→75%) ─────────────
        log.info("Step 5/7: Scanning Reddit for opportunities")
        update_auto_pipeline(db, pipeline_id, {
            "status": "scanning_opportunities",
            "progress": 65,
            "current_step": "Scanning Reddit for opportunities...",
        })

        opp_found = 0
        try:
            scan_req = ScanRequest(
                project_id=project_id,
                search_window_hours=72,
                max_posts_per_subreddit=10,
                min_score=MIN_RELEVANT_OPPORTUNITY_SCORE,
            )
            scan_run = run_scan(db, proj, scan_req)
            opp_found = scan_run["opportunities_found"]
            if opp_found == 0:
                fallback_scan_req = ScanRequest(
                    project_id=project_id,
                    search_window_hours=720,
                    max_posts_per_subreddit=10,
                    min_score=max(MIN_RELEVANT_OPPORTUNITY_SCORE - 10, 45),
                )
                fallback_scan_run = run_scan(db, proj, fallback_scan_req)
                opp_found = fallback_scan_run["opportunities_found"]
            log.info("Scan complete — %d opportunities found", opp_found)
        except Exception as e:
            log.warning("Scan step skipped or failed: %s", e)
            opp_found = 0
        update_auto_pipeline(db, pipeline_id, {"opportunities_found": opp_found, "progress": 75})

        # ── Step 6: Generate Drafts (75→95%) ────────────────────
        log.info("Step 6/7: Generating reply drafts")
        update_auto_pipeline(db, pipeline_id, {
            "status": "generating_drafts",
            "progress": 80,
            "current_step": "Generating reply drafts...",
        })

        from app.api.v1.deps import ensure_default_prompts
        ensure_default_prompts(db, project_id)
        prompts = list_prompt_templates_for_project(db, project_id)

        opportunities = list_opportunities_for_project(db, project_id, status="new", limit=10)

        drafts_count = 0
        for opp in opportunities:
            try:
                is_valid, _score = revalidate_opportunity(db, proj, opp)
                if not is_valid:
                    update_opportunity(db, opp["id"], {"status": "ignored"})
                    continue
                content, rationale, source_prompt = copilot.generate_reply(opp, {
                    "brand_name": website_analysis.brand_name,
                    "summary": website_analysis.summary,
                    "product_summary": website_analysis.product_summary,
                    "target_audience": website_analysis.target_audience,
                    "call_to_action": website_analysis.call_to_action,
                    "voice_notes": website_analysis.voice_notes,
                    "business_domain": website_analysis.business_domain,
                }, prompts)
                create_reply_draft(db, {
                    "project_id": project_id,
                    "opportunity_id": opp["id"],
                    "content": content,
                    "rationale": rationale,
                    "source_prompt": source_prompt,
                })
                update_opportunity(db, opp["id"], {"status": "drafting"})
                drafts_count += 1
            except Exception as e:
                log.warning("Draft generation failed for opp %s: %s", opp["id"], e)

        update_auto_pipeline(db, pipeline_id, {"drafts_generated": drafts_count, "progress": 95})
        log.info("Generated %d drafts for %d opportunities", drafts_count, len(opportunities))

        # ── Step 7: Finalize (95→100%) ──────────────────────────
        log.info("Step 7/7: Finalizing sales package")
        update_auto_pipeline(db, pipeline_id, {
            "current_step": "Finalizing sales package...",
        })

        update_auto_pipeline(db, pipeline_id, {
            "status": "ready",
            "progress": 100,
            "current_step": "Complete!",
            "completed_at": datetime.now(UTC).isoformat(),
        })

        # Create notification
        try:
            create_notification(db, {
                "workspace_id": workspace_id,
                "user_id": user_id,
                "title": "Sales Package Ready!",
                "body": f"Your auto-pipeline for {proj['name']} is complete. Review and launch your sales package.",
                "type": "opportunity",
            })
        except Exception as e:
            log.warning("Notification creation failed (non-fatal): %s", e)

        log.info("=== AUTO-PIPELINE COMPLETE === id=%s status=ready", pipeline_id)

    except Exception as e:
        log.error("=== AUTO-PIPELINE FAILED === id=%s error=%s\n%s", pipeline_id, e, traceback.format_exc())
        try:
            pipeline = get_auto_pipeline_by_id(db, pipeline_id)
            if pipeline:
                update_auto_pipeline(db, pipeline_id, {
                    "status": "error",
                    "error_message": str(e)[:500],
                    "completed_at": datetime.now(UTC).isoformat(),
                })
        except Exception as inner:
            log.error("Failed to save error status: %s", inner)
