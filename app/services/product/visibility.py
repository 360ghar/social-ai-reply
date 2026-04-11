"""AI Visibility tracking: mention detection, citation extraction."""

import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class MentionDetector:
    """Detect brand and competitor mentions in AI responses."""

    @staticmethod
    def detect_mentions(response_text: str, brand_name: str, competitors: list = None) -> dict:
        if not response_text:
            return {"brand_mentioned": False, "competitor_mentions": [], "sentiment": "neutral"}

        text_lower = response_text.lower()
        brand_lower = brand_name.lower()

        brand_mentioned = False
        brand_variants = [brand_lower, brand_lower.replace(" ", ""), brand_lower.replace(" ", "-")]
        for variant in brand_variants:
            if re.search(r'\b' + re.escape(variant) + r'\b', text_lower):
                brand_mentioned = True
                break

        competitor_mentions = []
        for comp in (competitors or []):
            comp_lower = comp.lower()
            matches = re.findall(r'\b' + re.escape(comp_lower) + r'\b', text_lower)
            if matches:
                competitor_mentions.append({"name": comp, "count": len(matches)})

        positive_words = ["recommend", "excellent", "great", "best", "top", "leading", "popular", "trusted"]
        negative_words = ["avoid", "poor", "worst", "expensive", "limited", "lacking", "disappointing"]
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        sentiment = "positive" if pos_count > neg_count else ("negative" if neg_count > pos_count else "neutral")

        return {
            "brand_mentioned": brand_mentioned,
            "competitor_mentions": competitor_mentions,
            "sentiment": sentiment,
        }


class CitationExtractor:
    """Extract URLs and domains from AI responses."""

    URL_PATTERN = re.compile(r'https?://[^\s\)\]\"\'<>,]+')

    @staticmethod
    def extract_citations(response_text: str) -> list:
        if not response_text:
            return []
        urls = CitationExtractor.URL_PATTERN.findall(response_text)
        citations = []
        seen_urls = set()
        for url in urls:
            url = url.rstrip(".")
            if url in seen_urls:
                continue
            seen_urls.add(url)
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            content_type = CitationExtractor._classify_url(url, domain)
            citations.append({
                "url": url,
                "domain": domain,
                "title": None,
                "content_type": content_type,
            })
        return citations

    @staticmethod
    def _classify_url(url: str, domain: str) -> str:
        url_lower = url.lower()
        if any(x in domain for x in ["reddit.com", "quora.com", "forum"]):
            return "discussion"
        if any(x in url_lower for x in ["review", "rating", "compare"]):
            return "review"
        if any(x in url_lower for x in ["vs", "comparison", "alternative"]):
            return "comparison"
        if any(x in url_lower for x in ["tutorial", "guide", "how-to", "howto"]):
            return "tutorial"
        if any(x in domain for x in ["blog", "medium.com", "substack"]):
            return "blog"
        if any(x in domain for x in ["docs.", "documentation"]):
            return "documentation"
        return "article"
