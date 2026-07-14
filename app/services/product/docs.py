"""Automated Living Document Generation."""

import datetime
from typing import Any


def generate_markdown_report(
    company: dict[str, Any],
    keywords: list[dict[str, Any]],
    personas: list[dict[str, Any]],
    opportunities: list[dict[str, Any]]
) -> str:
    """Generate a cohesive Markdown intelligence report for a company."""

    now = datetime.datetime.now().strftime("%B %d, %Y %H:%M")
    name = company.get("name", "Unknown Company")
    pitch = company.get("description") or company.get("extracted_summary") or "No description available."
    audience = company.get("target_audience") or "No specific audience detected."
    voice = company.get("brand_voice") or "No specific brand voice detected."
    raw_competitors = company.get("competitors") or company.get("extracted_competitors") or ""

    comp_list = []
    if isinstance(raw_competitors, str):
        comp_list = [c.strip() for c in raw_competitors.split(",") if c.strip()]
    elif isinstance(raw_competitors, list):
        comp_list = raw_competitors

    md = f"# {name} Intelligence Report\n"
    md += f"Generated: {now}\n\n"

    md += "## Executive Summary\n"
    md += f"{pitch}\n\n"

    md += "## Brand Positioning\n"
    md += f"- **Target Audience**: {audience}\n"
    md += f"- **Brand Voice**: {voice}\n\n"

    md += "## Target Personas\n"
    if personas:
        for i, p in enumerate(personas, 1):
            md += f"### {i}. {p.get('name', 'Persona')}\n"
            md += f"- **Role**: {p.get('role', 'N/A')}\n"
            if p.get("summary"):
                md += f"- **Summary**: {p.get('summary')}\n"
            pain = p.get("pain_points")
            if pain:
                md += "- **Pain Points**:\n"
                if isinstance(pain, list):
                    for pp in pain:
                        md += f"  - {pp}\n"
                else:
                    md += f"  - {pain}\n"
            md += "\n"
    else:
        md += "No personas defined.\n\n"

    md += "## Competitive Landscape\n"
    if comp_list:
        for c in comp_list:
            md += f"- {c}\n"
    else:
        md += "No competitors detected.\n"
    md += "\n"

    md += "## Recommended Keywords\n"
    if keywords:
        kws = [(k.get("keyword") if isinstance(k, dict) else str(k)) for k in keywords if (k.get("keyword") if isinstance(k, dict) else k)]
        for kw in kws:
            md += f"- {kw}\n"
        md += "\n"
    else:
        md += "No keywords generated.\n\n"

    md += f"## Discovered Opportunities ({len(opportunities)} found)\n"
    if opportunities:
        # Only show top 10 in report
        for opp in sorted(opportunities, key=lambda x: x.get("score", 0), reverse=True)[:10]:
            score = opp.get("score", 0)
            source = opp.get("platform") or "reddit"
            title = opp.get("title") or opp.get("body", "No Title")
            title_trunc = (title[:100] + "...") if len(title) > 100 else title
            title_trunc = title_trunc.replace("\n", " ").replace("|", "")

            url = opp.get("post_url") or "#"
            md += f"- **[{title_trunc}]({url})** — *{source}* (Score: {score})\n"
        md += "\n"
    else:
        md += "No actionable opportunities discovered in this run.\n"

    return md
