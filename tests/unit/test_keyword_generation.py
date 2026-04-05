"""Unit tests for structured keyword generation and AI payload parsing."""

from app.db.models import BrandProfile
from app.services.product.copilot import ProductCopilot
from app.services.product.relevance import split_csv_terms


def _make_brand(**overrides):
    defaults = dict(
        id=1,
        project_id=1,
        brand_name="SignalFlow",
        summary="A better way to find relevant Reddit threads for founders and marketers.",
        product_summary="Discover relevant Reddit conversations and draft grounded replies.",
        target_audience="founders, growth marketers",
    )
    defaults.update(overrides)
    return BrandProfile(**defaults)


def test_generate_keywords_filters_generic_single_words():
    copilot = ProductCopilot()
    keywords = copilot.generate_keywords(_make_brand(), [], count=12)

    generated = {item.keyword for item in keywords}
    assert "way" not in generated
    assert "find" not in generated
    assert "you" not in generated


def test_generate_keywords_retains_specific_multiword_phrases():
    copilot = ProductCopilot()
    brand = _make_brand(
        brand_name="360Ghar",
        summary="VR-first property discovery for home buyers in India.",
        product_summary="Find verified property listings with immersive home tours.",
        target_audience="home buyers, real estate teams",
    )

    keywords = copilot.generate_keywords(brand, [], count=12)
    generated = {item.keyword for item in keywords}

    assert "property listings" in generated
    assert "home tours" in generated
    assert "home buyers" in generated


def test_generate_keywords_filters_ambiguous_terms_without_domain_context():
    copilot = ProductCopilot()
    brand = _make_brand(
        brand_name="360Ghar",
        summary="AI-powered real estate marketplace for home buyers and renters in India.",
        product_summary="Compare property listings, apartments, and home tours in one place.",
        target_audience="home buyers, renters, real estate agents",
    )

    keywords = copilot.generate_keywords(brand, [], count=12)
    generated = {item.keyword for item in keywords}

    assert "ai" not in generated
    assert "vr" not in generated
    assert "real" not in generated
    assert "real estate marketplace" in generated
    assert "property listings" in generated
    assert "home buyers" in generated


def test_generate_keywords_canonicalizes_audience_clauses_into_domain_phrases():
    copilot = ProductCopilot()
    brand = _make_brand(
        brand_name="360Ghar",
        summary="AI-powered real estate marketplace for home buyers and renters in Gurugram.",
        product_summary="Compare property listings, apartments, and home tours in one place.",
        target_audience=(
            "Property buyers, renters, and sellers in Gurugram, Haryana; "
            "real estate investors seeking transparency; and individuals looking for "
            "a hassle-free, tech-enabled property search experience."
        ),
    )

    keywords = copilot.generate_keywords(brand, [], count=15)
    generated = {item.keyword for item in keywords}

    assert "real estate investors" in generated
    assert "property search" in generated
    assert "estate investors seeking" not in generated
    assert "individuals looking" not in generated


def test_split_csv_terms_preserves_geo_qualifiers_without_orphaning_locations():
    terms = split_csv_terms(
        "Property buyers, renters, and sellers in Gurugram, Haryana; "
        "real estate investors seeking transparency; and individuals looking for "
        "a hassle-free, tech-enabled property search experience."
    )

    assert "sellers in gurugram haryana" in terms
    assert "real estate investors seeking transparency" in terms
    assert "individuals looking for a hassle free tech enabled property search experience" in terms
    assert "haryana" not in terms


def test_parse_json_payload_handles_wrapped_or_noisy_json():
    copilot = ProductCopilot()

    payload = copilot._parse_json_payload(
        """```json
{"brand_name":"SignalFlow","summary":"Relevant Reddit discovery"}
```
Additional notes that should be ignored.
"""
    )

    assert payload == {"brand_name": "SignalFlow", "summary": "Relevant Reddit discovery"}
