"""Persona generation from brand context."""

from __future__ import annotations

from app.services.product.relevance import canonicalize_keyword_phrase, normalize_phrase, split_csv_terms


def suggest_personas(brand: dict | None, count: int = 4) -> list[dict]:
    """Generate persona suggestions from brand target audience."""
    seed = split_csv_terms(brand.get("target_audience") if brand and brand.get("target_audience") else "founders, marketers, operators")
    if not seed:
        seed = ["founders", "marketers", "operators"]
    personas = []
    seen_labels: set[str] = set()
    for idx, base in enumerate(seed, start=1):
        canonical = canonicalize_keyword_phrase(base, max_words=4) or normalize_phrase(base)
        label = canonical.strip().title() or f"Persona {idx}"
        if not label or label.lower() in seen_labels:
            continue
        seen_labels.add(label.lower())
        personas.append(
            {
                "name": label,
                "role": label,
                "summary": f"{label} wants trustworthy information and relevant options before making a decision.",
                "pain_points": ["Too much noise", "Hard to verify quality", "Needs trusted guidance"],
                "goals": ["Find relevant options", "Reduce decision risk"],
                "triggers": ["A new need appears", "Current options feel unreliable"],
                "preferred_subreddits": [],
                "source": "generated",
            }
        )
        if len(personas) >= count:
            break
    return personas
