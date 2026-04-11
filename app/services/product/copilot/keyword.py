"""Keyword generation from brand and persona context."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.product.relevance import (
    AMBIGUOUS_CONTEXTLESS_TERMS,
    ROLE_TERMS,
    build_domain_context,
    check_domain_vocabulary_match,
    extract_geo_terms,
    extract_structured_phrases,
    keyword_matches_domain_context,
    keyword_specificity,
    normalize_phrase,
    select_high_signal_keywords,
)


@dataclass
class GeneratedKeyword:
    """A generated keyword with metadata."""

    keyword: str
    rationale: str
    priority_score: int
    specificity: int = 0


def generate_keywords(
    brand: dict | None,
    personas: list[dict],
    count: int = 12,
) -> list[GeneratedKeyword]:
    """Generate keywords from brand and persona context.

    Args:
        brand: Brand profile dict containing brand_name, summary, product_summary,
               target_audience, and business_domain.
        personas: List of persona dicts with name, role, summary, pain_points, etc.
        count: Maximum number of keywords to generate (default 12).

    Returns:
        List of GeneratedKeyword dataclasses, sorted by priority score.
    """
    if not brand:
        return []
    phrase_map: dict[str, tuple[str, int]] = {}

    def add_candidate(keyword: str, rationale: str, base_score: int) -> None:
        normalized = normalize_phrase(keyword)
        if not normalized:
            return
        specificity = keyword_specificity(normalized)
        if normalized != normalize_phrase(brand.get("brand_name") or "") and specificity < 42:
            return
        score = max(min(base_score + specificity // 5, 100), 1)
        previous = phrase_map.get(normalized)
        if previous and previous[1] >= score:
            return
        phrase_map[normalized] = (rationale, score)

    if brand.get("brand_name"):
        add_candidate(brand.get("brand_name", ""), "Track direct brand mentions and exact product references.", 95)

    biz_domain = brand.get("business_domain", "") or ""
    base_domain_context = build_domain_context(
        brand_name=brand.get("brand_name"),
        summary=brand.get("summary"),
        product_summary=brand.get("product_summary"),
        target_audience=brand.get("target_audience"),
        business_domain=biz_domain,
    )

    summary_sources = [brand.get("product_summary") or "", brand.get("summary") or ""]
    for source in summary_sources:
        for phrase in extract_structured_phrases(source, limit=10):
            add_candidate(phrase, f"Specific product or problem phrase from the website copy: {phrase}.", 74)

    for audience in split_csv_terms(brand.get("target_audience")):
        base = 70 if len(audience.split()) > 1 else 58
        if audience in ROLE_TERMS:
            base -= 4
        add_candidate(audience, f"Audience phrase derived from the target audience: {audience}.", base)

    persona_sources: list[str] = []
    for persona in personas[:5]:
        persona_sources.extend([persona.get("name", ""), persona.get("role") or ""])
        if persona.get("source") != "generated":
            persona_sources.extend(
                [
                    persona.get("summary", ""),
                    " ".join(persona.get("pain_points") or []),
                    " ".join(persona.get("goals") or []),
                    " ".join(persona.get("triggers") or []),
                ]
            )
    for source in persona_sources:
        for phrase in extract_structured_phrases(source, limit=4):
            if not keyword_matches_domain_context(phrase, base_domain_context):
                continue
            add_candidate(phrase, f"Persona-driven phrase linked to a likely pain point or goal: {phrase}.", 68)

    domain_context = build_domain_context(
        brand_name=brand.get("brand_name"),
        summary=brand.get("summary"),
        product_summary=brand.get("product_summary"),
        target_audience=brand.get("target_audience"),
        keywords=list(phrase_map),
        extra_texts=[persona.get("name", "") for persona in personas[:5]],
        business_domain=biz_domain,
    )

    geo_source = " ".join(
        part
        for part in [
            brand.get("website_url") or "",
            brand.get("summary") or "",
            brand.get("product_summary") or "",
            brand.get("target_audience") or "",
        ]
        if part
    )
    for geo in extract_geo_terms(geo_source):
        add_candidate(geo, f"Geographic qualifier from the website context: {geo}.", 55)
    for phrase in domain_context.core_phrases[:8]:
        add_candidate(phrase, f"Canonical business-domain phrase distilled from the website context: {phrase}.", 76)
    for anchor in domain_context.anchor_terms[:6]:
        add_candidate(anchor, f"High-signal domain term repeated across the website context: {anchor}.", 58)

    ranked_keywords = select_high_signal_keywords(
        list(phrase_map),
        brand_name=brand.get("brand_name"),
        limit=count * 2,
        domain_context=domain_context,
    )

    # Domain-vocabulary post-filter
    if biz_domain:
        filtered_keywords: list[str] = []
        brand_norm = normalize_phrase(brand.get("brand_name") or "")
        for kw in ranked_keywords:
            if kw == brand_norm:
                filtered_keywords.append(kw)
                continue
            tokens = kw.split()
            meaningful = [t for t in tokens if t not in AMBIGUOUS_CONTEXTLESS_TERMS]
            if not meaningful:
                continue
            kw_domain_ok, _, _ = check_domain_vocabulary_match(kw, biz_domain)
            kw_has_anchor = bool(set(meaningful) & set(domain_context.anchor_terms))
            if not kw_domain_ok and not kw_has_anchor and all(
                t in AMBIGUOUS_CONTEXTLESS_TERMS or len(t) < 4 for t in tokens
            ):
                continue
            filtered_keywords.append(kw)
        ranked_keywords = filtered_keywords

    generated: list[GeneratedKeyword] = []
    for keyword in ranked_keywords:
        rationale, score = phrase_map.get(
            keyword,
            ("Derived from the brand context.", keyword_specificity(keyword)),
        )
        generated.append(
            GeneratedKeyword(
                keyword=keyword,
                rationale=rationale,
                priority_score=score,
                specificity=keyword_specificity(keyword),
            )
        )
        if len(generated) >= count:
            break
    return generated


# Need to import this here to avoid circular dependency
from app.services.product.relevance import split_csv_terms  # noqa: E402
