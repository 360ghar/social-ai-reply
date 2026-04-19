from unittest.mock import patch

from app.db.tables.analytics import create_auto_pipeline, get_auto_pipeline_by_id
from app.db.tables.projects import create_project
from app.services.product.copilot import GeneratedKeyword, WebsiteAnalysis
from app.services.product.pipeline import run_auto_pipeline_background


def test_run_auto_pipeline_background_marks_scan_failures_as_failed(mock_supabase):
    project = create_project(
        mock_supabase,
        {
            "workspace_id": 1,
            "name": "Pipeline Project",
            "slug": "pipeline-project",
            "description": "",
            "status": "active",
        },
    )
    pipeline = create_auto_pipeline(
        mock_supabase,
        {
            "id": "pipe_scan_fail",
            "project_id": project["id"],
            "website_url": "https://example.com",
            "status": "analyzing",
            "progress": 0,
            "current_step": "Analyzing website...",
            "started_at": "2026-04-19T00:00:00+00:00",
        },
    )

    with (
        patch("app.db.supabase_client.get_supabase_client", return_value=mock_supabase),
        patch(
            "app.services.product.pipeline.ProductCopilot.analyze_website",
            return_value=WebsiteAnalysis(
                brand_name="Example",
                summary="Example summary",
                product_summary="Find and verify relevant property listings.",
                target_audience="home buyers",
                call_to_action="Offer practical next steps.",
                voice_notes="Helpful and direct",
                business_domain="real estate",
            ),
        ),
        patch(
            "app.services.product.pipeline.ProductCopilot.suggest_personas",
            return_value=[
                {
                    "name": "Buyer",
                    "role": "Researcher",
                    "summary": "Needs help evaluating listings.",
                    "pain_points": ["Fake listings"],
                    "goals": ["Find trustworthy options"],
                    "triggers": ["Need verification"],
                    "preferred_subreddits": ["realestate"],
                }
            ],
        ),
        patch(
            "app.services.product.pipeline.ProductCopilot.generate_keywords",
            return_value=[
                GeneratedKeyword(
                    keyword="property listings",
                    rationale="High-intent real-estate phrase.",
                    priority_score=92,
                )
            ],
        ),
        patch(
            "app.services.product.pipeline.discover_and_store_subreddits",
            return_value=[{"name": "realestate"}],
        ),
        patch(
            "app.services.product.pipeline.run_scan",
            side_effect=RuntimeError("column scan_runs.search_window_hours does not exist"),
        ),
    ):
        run_auto_pipeline_background(
            pipeline["id"],
            "https://example.com",
            project["id"],
            workspace_id=1,
            user_id=1,
        )

    refreshed = get_auto_pipeline_by_id(mock_supabase, pipeline["id"])
    assert refreshed is not None
    assert refreshed["status"] == "failed"
    assert "Opportunity scan failed" in refreshed["error_message"]
    assert "search_window_hours" in refreshed["error_message"]
