"""AI Visibility tracking: model runners, mention detection, citation extraction."""
import logging
import re
from urllib.parse import urlparse

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ModelRunner:
    """Execute prompts across AI models and extract brand/citation data."""

    def __init__(self):
        settings = get_settings()
        self.gemini_api_key = settings.gemini_api_key
        self.gemini_model = settings.gemini_model or "gemini-3-flash-preview"
        self.gemini_api_url = settings.gemini_api_url or "https://generativelanguage.googleapis.com/v1beta"
        # Keep OpenAI as fallback
        self.openai_client = None
        if settings.openai_api_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=settings.openai_api_key)
            except ImportError:
                logger.warning("OpenAI package not installed")

    def run_prompt(self, prompt: str, model_name: str) -> str | None:
        try:
            if model_name in ("chatgpt", "openai"):
                # Try OpenAI first, fall back to Gemini
                if self.openai_client:
                    return self._run_openai(prompt)
                elif self.gemini_api_key:
                    return self._run_gemini(prompt)
                return self._simulate_response(prompt, model_name)
            elif model_name == "perplexity":
                return self._run_perplexity(prompt)
            elif model_name == "gemini":
                return self._run_gemini(prompt)
            elif model_name == "claude":
                return self._run_claude(prompt)
            else:
                logger.warning(f"Unknown model: {model_name}")
                return None
        except Exception as e:
            logger.error(f"Model runner error ({model_name}): {e}")
            return None

    def _run_openai(self, prompt: str) -> str | None:
        if not self.openai_client:
            return None
        settings = get_settings()
        try:
            resp = self.openai_client.chat.completions.create(
                model=settings.openai_model or "gpt-4-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Answer the user's question thoroughly with specific product and brand recommendations where relevant. Include URLs to sources when possible."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2048,
                temperature=0.7,
            )
            return resp.choices[0].message.content if resp.choices else None
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None

    def _run_perplexity(self, prompt: str) -> str | None:
        """Perplexity API via OpenAI-compatible endpoint."""
        settings = get_settings()
        perplexity_key = getattr(settings, "perplexity_api_key", None)
        if not perplexity_key:
            logger.info("Perplexity API key not set, using simulation")
            return self._simulate_response(prompt, "perplexity")
        try:
            from openai import OpenAI
            client = OpenAI(api_key=perplexity_key, base_url="https://api.perplexity.ai")
            resp = client.chat.completions.create(
                model="llama-3.1-sonar-large-128k-online",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
            )
            return resp.choices[0].message.content if resp.choices else None
        except Exception as e:
            logger.error(f"Perplexity API error: {e}")
            return None

    def _run_gemini(self, prompt: str) -> str | None:
        if not self.gemini_api_key:
            logger.info("Gemini API key not set, using simulation")
            return self._simulate_response(prompt, "gemini")
        try:
            import httpx
            url = f"{self.gemini_api_url}/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
            resp = httpx.post(
                url,
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=30,
            )
            data = resp.json()
            return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None

    def _run_claude(self, prompt: str) -> str | None:
        settings = get_settings()
        claude_key = getattr(settings, "anthropic_api_key", None)
        if not claude_key:
            logger.info("Claude API key not set, using simulation")
            return self._simulate_response(prompt, "claude")
        try:
            import httpx
            resp = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": claude_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-sonnet-4-20250514", "max_tokens": 2048, "messages": [{"role": "user", "content": prompt}]},
                timeout=30,
            )
            data = resp.json()
            return data.get("content", [{}])[0].get("text")
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return None

    def _simulate_response(self, prompt: str, model: str) -> str:
        """Simulation for models without API keys. Returns a reasonable mock response."""
        return f"[Simulated {model} response] Based on my analysis, I'd recommend looking into several options for this query. There are many tools available in this space. For more details, check relevant sources online."


class MentionDetector:
    """Detect brand and competitor mentions in AI responses."""

    @staticmethod
    def detect_mentions(response_text: str, brand_name: str, competitors: list = None) -> dict:
        if not response_text:
            return {"brand_mentioned": False, "competitor_mentions": [], "sentiment": "neutral"}

        text_lower = response_text.lower()
        brand_lower = brand_name.lower()

        brand_mentioned = brand_lower in text_lower
        brand_variants = [brand_lower, brand_lower.replace(" ", ""), brand_lower.replace(" ", "-")]
        for variant in brand_variants:
            if variant in text_lower:
                brand_mentioned = True
                break

        competitor_mentions = []
        for comp in (competitors or []):
            comp_lower = comp.lower()
            if comp_lower in text_lower:
                count = text_lower.count(comp_lower)
                competitor_mentions.append({"name": comp, "count": count})

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
