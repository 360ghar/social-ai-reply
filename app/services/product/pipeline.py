"""Background task to run the auto-pipeline from website URL to sales package."""

import logging
import traceback
from datetime import UTC, datetime

from app.db.models import (
    AutoPipeline,
    BrandProfile,
    DiscoveryKeyword,
    MonitoredSubreddit,
    Opportunity,
    OpportunityStatus,
    Persona,
    Project,
    PromptTemplate,
    ReplyDraft,
)
from app.db.models import (
    Notification as NotificationModel,
)
from app.db.session import SessionLocal
from app.schemas.v1.discovery import ScanRequest
from app.services.product.copilot import ProductCopilot
from app.services.product.discovery import discover_and_store_subreddits
from app.services.product.scanner import revalidate_opportunity, run_scan
from app.services.product.scoring import MIN_RELEVANT_OPPORTUNITY_SCORE

log = logging.getLogger("redditflow.pipeline")
TARGET_PIPELINE_SUBREDDITS = 6


def run_auto_pipeline_background(
    pipeline_id: str,
    website_url: str,
    project_id: int,
    workspace_id: int,
    user_id: int,
):
    log.info("=== AUTO-PIPELINE START === id=%s url=%s project=%s", pipeline_id, website_url, project_id)

    db = SessionLocal()
    try:
        pipeline = db.query(AutoPipeline).filter(AutoPipeline.id == pipeline_id).first()
        if not pipeline:
            log.error("Pipeline %s not found in DB — aborting.", pipeline_id)
            return

        proj = db.query(Project).filter(Project.id == project_id).first()
        if not proj:
            log.error("Project %s not found in DB — aborting.", project_id)
            return

        copilot = ProductCopilot()
        log.info("Step 1/7: Analyzing website %s", website_url)

        # ── Step 1: Analyze Website (0→15%) ─────────────────────
        pipeline.status = "analyzing"
        pipeline.progress = 5
        pipeline.current_step = "Analyzing website content..."
        db.commit()

        try:
            website_analysis = copilot.analyze_website(website_url)
            log.info("Website analysis OK — brand=%s summary_len=%d",
                     website_analysis.brand_name, len(website_analysis.summary or ""))
        except Exception as e:
            log.error("Website analysis FAILED: %s\n%s", e, traceback.format_exc())
            raise

        pipeline.brand_summary = website_analysis.summary
        pipeline.progress = 15

        brand = db.query(BrandProfile).filter(BrandProfile.project_id == proj.id).first()
        if brand:
            brand.brand_name = website_analysis.brand_name
            brand.summary = website_analysis.summary
            brand.product_summary = website_analysis.product_summary
            brand.target_audience = website_analysis.target_audience
            brand.call_to_action = website_analysis.call_to_action
            brand.voice_notes = website_analysis.voice_notes
            brand.business_domain = website_analysis.business_domain
            log.info("Updated existing BrandProfile id=%s", brand.id)
        else:
            brand = BrandProfile(
                project_id=proj.id,
                brand_name=website_analysis.brand_name,
                website_url=website_url,
                summary=website_analysis.summary,
                product_summary=website_analysis.product_summary,
                target_audience=website_analysis.target_audience,
                call_to_action=website_analysis.call_to_action,
                voice_notes=website_analysis.voice_notes,
                business_domain=website_analysis.business_domain,
            )
            db.add(brand)
            log.info("Created new BrandProfile for project %s", proj.id)
        db.commit()

        # ── Step 2: Generate Personas (15→30%) ──────────────────
        log.info("Step 2/7: Generating personas")
        pipeline.status = "generating_personas"
        pipeline.progress = 20
        pipeline.current_step = "Generating target personas..."
        db.commit()

        try:
            personas_data = copilot.suggest_personas(brand, count=4)
            log.info("Generated %d personas", len(personas_data))
        except Exception as e:
            log.error("Persona generation FAILED: %s\n%s", e, traceback.format_exc())
            raise

        for p_data in personas_data:
            persona = Persona(
                project_id=proj.id,
                name=p_data["name"],
                role=p_data.get("role"),
                summary=p_data["summary"],
                pain_points=p_data.get("pain_points", []),
                goals=p_data.get("goals", []),
                triggers=p_data.get("triggers", []),
                preferred_subreddits=p_data.get("preferred_subreddits", []),
                source="generated",
            )
            db.add(persona)
        pipeline.personas_generated = len(personas_data)
        pipeline.progress = 30
        db.commit()

        # ── Step 3: Discover Keywords (30→45%) ──────────────────
        log.info("Step 3/7: Discovering keywords")
        pipeline.status = "discovering_keywords"
        pipeline.progress = 35
        pipeline.current_step = "Discovering relevant keywords..."
        db.commit()

        personas_list = db.query(Persona).filter(Persona.project_id == proj.id).all()
        try:
            keywords_data = copilot.generate_keywords(brand, personas_list, count=15)
            log.info("Generated %d keywords", len(keywords_data))
        except Exception as e:
            log.error("Keyword generation FAILED: %s\n%s", e, traceback.format_exc())
            raise

        existing_kw = {
            row.keyword
            for row in db.query(DiscoveryKeyword.keyword).filter(
                DiscoveryKeyword.project_id == proj.id
            ).all()
        }
        new_kw_count = 0
        for k_data in keywords_data:
            if k_data.keyword in existing_kw:
                log.info("Keyword '%s' already exists — skipping", k_data.keyword)
                continue
            keyword = DiscoveryKeyword(
                project_id=proj.id,
                keyword=k_data.keyword,
                rationale=k_data.rationale,
                priority_score=k_data.priority_score,
                source="generated",
            )
            db.add(keyword)
            existing_kw.add(k_data.keyword)
            new_kw_count += 1
        pipeline.keywords_generated = len(keywords_data)
        pipeline.progress = 45
        db.commit()
        log.info("Inserted %d new keywords (%d already existed)", new_kw_count, len(keywords_data) - new_kw_count)

        # ── Step 4: Discover Subreddits (45→60%) ────────────────
        log.info("Step 4/7: Discovering subreddits")
        pipeline.status = "finding_subreddits"
        pipeline.progress = 50
        pipeline.current_step = "Discovering relevant subreddits..."
        db.commit()

        existing_sub_count = db.query(MonitoredSubreddit).filter(
            MonitoredSubreddit.project_id == proj.id,
            MonitoredSubreddit.is_active.is_(True),
        ).count()
        subreddits_to_discover = max(TARGET_PIPELINE_SUBREDDITS - existing_sub_count, 0)
        try:
            if subreddits_to_discover > 0:
                created_subreddits = discover_and_store_subreddits(
                    db,
                    proj,
                    max_subreddits=subreddits_to_discover,
                )
                discovered_subreddits = [row.name for row in created_subreddits]
            else:
                discovered_subreddits = []
                log.info(
                    "Skipping subreddit discovery because project %s already has %d active subreddits",
                    proj.id,
                    existing_sub_count,
                )
        except Exception as e:
            log.warning("Shared subreddit discovery failed: %s", e)
            discovered_subreddits = []

        pipeline.subreddits_found = existing_sub_count + len(discovered_subreddits)
        pipeline.progress = 60
        db.commit()
        log.info("Discovered %d new subreddits (%d already existed)", len(discovered_subreddits), existing_sub_count)

        # ── Step 5: Scan for Opportunities (60→75%) ─────────────
        log.info("Step 5/7: Scanning Reddit for opportunities")
        pipeline.status = "scanning_opportunities"
        pipeline.progress = 65
        pipeline.current_step = "Scanning Reddit for opportunities..."
        db.commit()

        opp_found = 0
        try:
            scan_req = ScanRequest(
                project_id=proj.id,
                search_window_hours=72,
                max_posts_per_subreddit=10,
                min_score=MIN_RELEVANT_OPPORTUNITY_SCORE,
            )
            scan_run = run_scan(db, proj, scan_req)
            opp_found = scan_run.opportunities_found
            if opp_found == 0:
                fallback_scan_req = ScanRequest(
                    project_id=proj.id,
                    search_window_hours=720,
                    max_posts_per_subreddit=10,
                    min_score=max(MIN_RELEVANT_OPPORTUNITY_SCORE - 10, 45),
                )
                fallback_scan_run = run_scan(db, proj, fallback_scan_req)
                opp_found = fallback_scan_run.opportunities_found
            log.info("Scan complete — %d opportunities found", opp_found)
        except Exception as e:
            log.warning("Scan step skipped or failed: %s", e)
            opp_found = 0
        pipeline.opportunities_found = opp_found
        pipeline.progress = 75
        db.commit()

        # ── Step 6: Generate Drafts (75→95%) ────────────────────
        log.info("Step 6/7: Generating reply drafts")
        pipeline.status = "generating_drafts"
        pipeline.progress = 80
        pipeline.current_step = "Generating reply drafts..."
        db.commit()

        from app.api.v1.deps import ensure_default_prompts
        ensure_default_prompts(db, proj.id)
        prompts = db.query(PromptTemplate).filter(PromptTemplate.project_id == proj.id).all()

        opportunities = db.query(Opportunity).filter(
            Opportunity.project_id == proj.id,
            Opportunity.status == OpportunityStatus.NEW,
        ).order_by(Opportunity.score.desc()).limit(10).all()

        drafts_count = 0
        for opp in opportunities:
            try:
                is_valid, _score = revalidate_opportunity(db, proj, opp)
                if not is_valid:
                    opp.status = OpportunityStatus.IGNORED
                    continue
                content, rationale, source_prompt = copilot.generate_reply(opp, brand, prompts)
                reply_draft = ReplyDraft(
                    project_id=proj.id,
                    opportunity_id=opp.id,
                    content=content,
                    rationale=rationale,
                    source_prompt=source_prompt,
                )
                db.add(reply_draft)
                opp.status = OpportunityStatus.DRAFTING
                drafts_count += 1
            except Exception as e:
                log.warning("Draft generation failed for opp %s: %s", opp.id, e)

        db.commit()
        pipeline.drafts_generated = drafts_count
        pipeline.progress = 95
        db.commit()
        log.info("Generated %d drafts for %d opportunities", drafts_count, len(opportunities))

        # ── Step 7: Finalize (95→100%) ──────────────────────────
        log.info("Step 7/7: Finalizing sales package")
        pipeline.current_step = "Finalizing sales package..."
        db.commit()

        pipeline.status = "ready"
        pipeline.progress = 100
        pipeline.current_step = "Complete!"
        pipeline.completed_at = datetime.now(UTC)
        db.commit()

        # Create notification
        try:
            notification = NotificationModel(
                workspace_id=workspace_id,
                user_id=user_id,
                title="Sales Package Ready!",
                body=f"Your auto-pipeline for {proj.name} is complete. Review and launch your sales package.",
                type="opportunity",
            )
            db.add(notification)
            db.commit()
        except Exception as e:
            log.warning("Notification creation failed (non-fatal): %s", e)

        log.info("=== AUTO-PIPELINE COMPLETE === id=%s status=ready", pipeline_id)

    except Exception as e:
        log.error("=== AUTO-PIPELINE FAILED === id=%s error=%s\n%s", pipeline_id, e, traceback.format_exc())
        try:
            db.rollback()
            pipeline = db.query(AutoPipeline).filter(AutoPipeline.id == pipeline_id).first()
            if pipeline:
                pipeline.status = "error"
                pipeline.error_message = str(e)[:500]
                pipeline.completed_at = datetime.now(UTC)
                db.commit()
        except Exception as inner:
            log.error("Failed to save error status: %s", inner)
    finally:
        db.close()
