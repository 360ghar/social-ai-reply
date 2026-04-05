import json
import logging
import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.db.models import BrandProfile, Opportunity, Persona, PromptTemplate
from app.services.product.relevance import (
    AMBIGUOUS_CONTEXTLESS_TERMS,
    ROLE_TERMS,
    build_domain_context,
    canonicalize_keyword_phrase,
    check_domain_vocabulary_match,
    extract_geo_terms,
    extract_structured_phrases,
    keyword_matches_domain_context,
    keyword_specificity,
    normalize_phrase,
    select_high_signal_keywords,
    split_csv_terms,
)

logger = logging.getLogger(__name__)


@dataclass
class WebsiteAnalysis:
    brand_name: str
    summary: str
    product_summary: str
    target_audience: str
    call_to_action: str
    voice_notes: str
    business_domain: str = ""


@dataclass
class GeneratedKeyword:
    keyword: str
    rationale: str
    priority_score: int
    specificity: int = 0


class ProductCopilot:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.gemini_api_key or settings.openai_api_key
        self.use_ai = bool(self.api_key) and "PYTEST_CURRENT_TEST" not in os.environ
        self.model = settings.gemini_model or "gemini-2-flash-preview"
        self.api_url = settings.gemini_api_url or "https://generativelanguage.googleapis.com/v1beta"
        self.user_agent = settings.reddit_user_agent

    # ── Website fetching ──────────────────────────────────────────

    _BROWSER_UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Ensure the URL has a scheme (default https)."""
        url = url.strip()
        if not url:
            raise ValueError("Empty website URL.")
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        return url

    def _fetch_html(self, url: str) -> str:
        """Fetch website HTML with retries, SSL fallback, and a real browser UA."""
        headers = {
            "User-Agent": self._BROWSER_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        last_err: Exception | None = None

        for verify_ssl in (True, False):
            try:
                with httpx.Client(
                    timeout=25.0,
                    follow_redirects=True,
                    verify=verify_ssl,
                ) as client:
                    resp = client.get(url, headers=headers)
                    resp.raise_for_status()
                    return resp.text
            except httpx.HTTPStatusError as exc:
                logger.warning("HTTP %s for %s (ssl_verify=%s)", exc.response.status_code, url, verify_ssl)
                last_err = exc
                # Don't retry status errors with SSL off — won't help
                break
            except (httpx.ConnectError, httpx.TimeoutException, Exception) as exc:
                logger.warning("Fetch failed for %s (ssl_verify=%s): %s", url, verify_ssl, exc)
                last_err = exc
                if verify_ssl:
                    logger.info("Retrying %s with SSL verification disabled...", url)
                    continue
                break

        raise RuntimeError(f"Could not fetch {url}: {last_err}") from last_err

    def analyze_website(self, website_url: str) -> WebsiteAnalysis:
        website_url = self._normalize_url(website_url)
        html = self._fetch_html(website_url)

        soup = BeautifulSoup(html, "html.parser")
        title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
        description_tag = soup.find("meta", attrs={"name": "description"})
        description = (description_tag.get("content") or "").strip() if description_tag else ""
        headings = " ".join(tag.get_text(" ", strip=True) for tag in soup.find_all(["h1", "h2"])[:6])
        paragraphs = " ".join(tag.get_text(" ", strip=True) for tag in soup.find_all("p")[:10])
        text = " ".join(part for part in [title, description, headings, paragraphs] if part).strip()
        cleaned = re.sub(r"\s+", " ", text)
        fallback_name = urlparse(website_url).netloc.replace("www.", "").split(".")[0].replace("-", " ").title()
        summary = cleaned[:500] or f"{fallback_name} helps customers solve a focused problem."
        if self.use_ai:
            ai_result = self._structured_brand_analysis(cleaned or fallback_name, fallback_name)
            if ai_result:
                return ai_result
        return WebsiteAnalysis(
            brand_name=title.split("|")[0].strip() or fallback_name,
            summary=summary[:280],
            product_summary=(description or summary[:220])[:280],
            target_audience=self._infer_audience(summary),
            call_to_action=self._infer_cta(summary),
            voice_notes="Helpful, specific, non-spammy, and conversational.",
            business_domain=self._infer_business_domain(summary, description),
        )

    def suggest_personas(self, brand: BrandProfile | None, count: int = 4) -> list[dict]:
        seed = split_csv_terms(brand.target_audience if brand and brand.target_audience else "founders, marketers, operators")
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

    def generate_keywords(
        self,
        brand: BrandProfile | None,
        personas: list[Persona],
        count: int = 12,
    ) -> list[GeneratedKeyword]:
        if not brand:
            return []
        phrase_map: dict[str, tuple[str, int]] = {}

        def add_candidate(keyword: str, rationale: str, base_score: int) -> None:
            normalized = normalize_phrase(keyword)
            if not normalized:
                return
            specificity = keyword_specificity(normalized)
            if normalized != normalize_phrase(brand.brand_name or "") and specificity < 42:
                return
            score = max(min(base_score + specificity // 5, 100), 1)
            previous = phrase_map.get(normalized)
            if previous and previous[1] >= score:
                return
            phrase_map[normalized] = (rationale, score)

        if brand.brand_name:
            add_candidate(brand.brand_name, "Track direct brand mentions and exact product references.", 95)

        biz_domain = getattr(brand, "business_domain", "") or ""
        base_domain_context = build_domain_context(
            brand_name=brand.brand_name,
            summary=brand.summary,
            product_summary=brand.product_summary,
            target_audience=brand.target_audience,
            business_domain=biz_domain,
        )

        summary_sources = [brand.product_summary or "", brand.summary or ""]
        for source in summary_sources:
            for phrase in extract_structured_phrases(source, limit=10):
                add_candidate(phrase, f"Specific product or problem phrase from the website copy: {phrase}.", 74)

        for audience in split_csv_terms(brand.target_audience):
            base = 70 if len(audience.split()) > 1 else 58
            if audience in ROLE_TERMS:
                base -= 4
            add_candidate(audience, f"Audience phrase derived from the target audience: {audience}.", base)

        persona_sources: list[str] = []
        for persona in personas[:5]:
            persona_sources.extend([persona.name, persona.role or ""])
            if persona.source != "generated":
                persona_sources.extend(
                    [
                        persona.summary,
                        " ".join(persona.pain_points or []),
                        " ".join(persona.goals or []),
                        " ".join(persona.triggers or []),
                    ]
                )
        for source in persona_sources:
            for phrase in extract_structured_phrases(source, limit=4):
                if not keyword_matches_domain_context(phrase, base_domain_context):
                    continue
                add_candidate(phrase, f"Persona-driven phrase linked to a likely pain point or goal: {phrase}.", 68)

        domain_context = build_domain_context(
            brand_name=brand.brand_name,
            summary=brand.summary,
            product_summary=brand.product_summary,
            target_audience=brand.target_audience,
            keywords=list(phrase_map),
            extra_texts=[persona.name for persona in personas[:5]],
            business_domain=biz_domain,
        )

        geo_source = " ".join(
            part
            for part in [
                brand.website_url or "",
                brand.summary or "",
                brand.product_summary or "",
                brand.target_audience or "",
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
            brand_name=brand.brand_name,
            limit=count * 2,
            domain_context=domain_context,
        )

        # ── Domain-vocabulary post-filter ─────────────────────────────
        # When a business domain is known, drop keywords composed entirely
        # of ambiguous tech/modifier terms (e.g. "vr", "ai powered") that
        # would match posts outside the domain.
        if biz_domain:
            filtered_keywords: list[str] = []
            brand_norm = normalize_phrase(brand.brand_name or "")
            for kw in ranked_keywords:
                if kw == brand_norm:
                    filtered_keywords.append(kw)
                    continue
                tokens = kw.split()
                meaningful = [t for t in tokens if t not in AMBIGUOUS_CONTEXTLESS_TERMS]
                if not meaningful:
                    # All tokens are ambiguous (e.g. "vr", "ai powered") — skip
                    continue
                # Check if keyword has at least one domain-relevant token
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

    def generate_reply(
        self,
        opportunity: Opportunity,
        brand: BrandProfile | None,
        prompts: list[PromptTemplate],
    ) -> tuple[str, str, str]:
        prompt_context = "\n".join(
            f"{prompt.name}: {prompt.instructions}" for prompt in prompts if prompt.prompt_type == "reply"
        )
        if self.use_ai:
            ai_reply = self._ai_reply(opportunity, brand, prompt_context)
            if ai_reply:
                return ai_reply

        cta = (brand.call_to_action if brand and brand.call_to_action else "offer a concise next step").strip(".")
        brand_name = brand.brand_name if brand else "our team"
        content = (
            "You're not the only one dealing with this. A practical way to approach it is to start with the "
            "constraint that is slowing progress the most, test one small fix, and compare the before/after signal. "
            "We've seen teams similar to yours benefit from documenting what changed and why before expanding "
            "the solution."
        )
        rationale = (
            "The draft stays non-promotional, responds to the stated problem, and leaves room for a follow-up "
            f"where {brand_name} can help if the thread invites it."
        )
        source_prompt = prompt_context or cta
        return content, rationale, source_prompt

    def generate_post(self, brand: BrandProfile | None, prompts: list[PromptTemplate]) -> tuple[str, str, str]:
        prompt_context = "\n".join(
            f"{prompt.name}: {prompt.instructions}" for prompt in prompts if prompt.prompt_type == "post"
        )
        if self.use_ai:
            ai_post = self._ai_post(brand, prompt_context)
            if ai_post:
                return ai_post

        brand_name = brand.brand_name if brand else "Your Product"
        title = f"What we learned shipping {brand_name} without relying on spammy growth loops"
        body = (
            "Three things changed our outcomes:\n\n"
            "1. We prioritized signal-rich customer conversations over volume.\n"
            "2. We documented repeat objections before changing our message.\n"
            "3. We treated every community interaction as trust building, not lead capture.\n\n"
            "If helpful, I can share the exact rubric we use to decide where to engage."
        )
        rationale = "The post is educational, specific, and designed to invite opt-in conversation."
        return title, body, rationale

    def _meaningful_terms(self, text: str) -> list[str]:
        stop_words = {
            "about",
            "after",
            "before",
            "brand",
            "helps",
            "their",
            "there",
            "these",
            "those",
            "with",
            "from",
            "that",
            "this",
            "your",
            "into",
            "have",
            "more",
            "less",
            "best",
            "over",
            "team",
        }
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", text.lower())
        unique = []
        seen: set[str] = set()
        for word in words:
            if word in stop_words or word in seen:
                continue
            seen.add(word)
            unique.append(word)
        return unique[:30]

    def _infer_audience(self, summary: str) -> str:
        lowered = summary.lower()
        if "developer" in lowered or "engineering" in lowered:
            return "developers, engineering leaders, technical founders"
        if "marketing" in lowered or "growth" in lowered:
            return "founders, growth marketers, demand gen teams"
        if "sales" in lowered:
            return "founders, sales leaders, revenue teams"
        return "founders, operators, marketing teams"

    def _infer_cta(self, summary: str) -> str:
        if "book" in summary.lower() or "demo" in summary.lower():
            return "Invite interested users to ask for the process or request a demo."
        return "Offer a useful next step only if the conversation naturally asks for it."

    def _infer_business_domain(self, summary: str, description: str = "") -> str:
        text = f"{summary} {description}".lower()
        domain_signals: dict[str, list[str]] = {
            "real estate": [
                "real estate", "property", "properties", "apartment", "apartments", "house", "houses",
                "rent", "rental", "mortgage", "realtor", "broker", "home buying", "home selling",
                "housing", "flat", "flats", "villa", "condo", "residential", "commercial property",
                "plot", "land", "construction", "builder", "ghar", "makaan", "bhk",
            ],
            "healthcare": [
                "health", "medical", "hospital", "doctor", "patient", "clinic", "pharma",
                "wellness", "therapy", "diagnosis", "treatment", "healthcare",
            ],
            "fintech": [
                "finance", "fintech", "banking", "payment", "invest", "loan", "credit",
                "insurance", "trading", "stock", "mutual fund", "wealth",
            ],
            "edtech": [
                "education", "edtech", "learning", "course", "student", "tutor", "university",
                "school", "training", "certification", "e-learning",
            ],
            "ecommerce": [
                "ecommerce", "e-commerce", "shop", "shopping", "store", "marketplace",
                "retail", "buy online", "sell online", "product catalog",
            ],
            "saas": [
                "saas", "software as a service", "cloud platform", "subscription software",
                "project management", "crm", "erp", "workflow automation",
            ],
            "travel": [
                "travel", "tourism", "hotel", "booking", "flight", "vacation", "trip",
                "destination", "hospitality",
            ],
            "food and restaurant": [
                "food", "restaurant", "delivery", "recipe", "cuisine", "dining", "chef",
                "catering", "meal",
            ],
            "marketing": [
                "marketing", "advertising", "seo", "social media marketing", "content marketing",
                "brand awareness", "lead generation", "digital marketing",
            ],
            "developer tools": [
                "developer", "api", "sdk", "devops", "ci/cd", "code", "programming",
                "framework", "library", "open source",
            ],
            "saas": [
                "saas", "software as a service", "subscription", "churn", "mrr", "arr",
                "onboarding", "freemium", "b2b", "b2c", "customer success", "pricing plan",
            ],
            "legal": [
                "legal", "lawyer", "attorney", "law firm", "contract", "litigation",
                "compliance", "regulation", "lawsuit", "court",
            ],
            "logistics": [
                "logistics", "shipping", "freight", "warehouse", "supply chain",
                "delivery", "fleet", "tracking", "fulfillment",
            ],
            "automotive": [
                "automotive", "car", "vehicle", "dealership", "mechanic", "repair",
                "ev", "electric vehicle", "test drive",
            ],
            "fitness": [
                "fitness", "gym", "workout", "exercise", "training", "personal trainer",
                "nutrition", "weight loss", "yoga", "crossfit",
            ],
        }
        best_domain = ""
        best_score = 0
        for domain, signals in domain_signals.items():
            score = sum(1 for signal in signals if signal in text)
            if score > best_score:
                best_score = score
                best_domain = domain
        return best_domain if best_score >= 2 else ""

    def _call_gemini(self, system_prompt: str, user_content: str, temperature: float = 0.2) -> dict | None:
        if not self.use_ai or not self.api_key:
            return None
        try:
            url = f"{self.api_url}/models/{self.model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": f"{system_prompt}\n\n{user_content}"}]}
                ],
                "generationConfig": {
                    "temperature": temperature,
                    "responseMimeType": "application/json"
                }
            }
            resp = httpx.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
            return self._parse_json_payload(text)
        except Exception:
            logger.exception("Gemini API call failed")
            return None

    def _structured_brand_analysis(self, text: str, fallback_name: str) -> WebsiteAnalysis | None:
        try:
            system_prompt = (
                "You extract go-to-market context for a Reddit engagement platform. "
                "Return JSON with brand_name, summary, product_summary, target_audience, call_to_action, voice_notes, "
                "and business_domain.\n\n"
                "business_domain MUST be a short label identifying the company's core industry or vertical "
                "(e.g. 'real estate', 'healthcare', 'fintech', 'edtech', 'ecommerce', 'saas', 'travel', "
                "'food and restaurant', 'marketing', 'developer tools', 'legal', 'logistics', 'automotive', etc.).\n\n"
                "product_summary should focus on the CORE business problem the company solves in its domain, "
                "NOT generic technology features like AI, VR, or automation. For example, if a real estate platform "
                "uses VR tours, the product_summary should emphasize real estate search and property discovery, "
                "not VR technology.\n\n"
                "target_audience should list the DOMAIN-SPECIFIC audience (e.g. 'home buyers, property investors, "
                "real estate agents' for a real estate platform), NOT generic tech users."
            )
            payload = self._call_gemini(system_prompt, text[:12000], temperature=0.2)
            if not payload:
                return None
            if isinstance(payload, list):
                payload = payload[0] if payload else {}
            if not isinstance(payload, dict):
                return None
            inferred_domain = payload.get("business_domain") or self._infer_business_domain(
                payload.get("summary") or text[:500],
                payload.get("product_summary") or "",
            )
            return WebsiteAnalysis(
                brand_name=payload.get("brand_name") or fallback_name,
                summary=payload.get("summary") or text[:280],
                product_summary=payload.get("product_summary") or text[:280],
                target_audience=payload.get("target_audience") or self._infer_audience(text),
                call_to_action=payload.get("call_to_action") or self._infer_cta(text),
                voice_notes=payload.get("voice_notes") or "Helpful, grounded, and specific.",
                business_domain=inferred_domain,
            )
        except Exception:
            logger.exception("_structured_brand_analysis failed")
            return None

    def _ai_reply(
        self,
        opportunity: Opportunity,
        brand: BrandProfile | None,
        prompt_context: str,
    ) -> tuple[str, str, str] | None:
        try:
            system_prompt = (
                "Write a useful Reddit reply. Avoid spam, avoid sounding salesy, do not mention the company unless "
                "asked. "
                "Return JSON with content and rationale."
            )
            brand_context = {
                "brand_name": brand.brand_name if brand else "",
                "summary": brand.summary if brand else "",
                "voice_notes": brand.voice_notes if brand else "",
                "cta": brand.call_to_action if brand else "",
            }
            user_content = json.dumps(
                {
                    "opportunity": {
                        "title": opportunity.title,
                        "body_excerpt": opportunity.body_excerpt,
                        "subreddit": opportunity.subreddit_name,
                        "score_reasons": opportunity.score_reasons,
                    },
                    "brand": brand_context,
                    "prompt_context": prompt_context,
                }
            )
            payload = self._call_gemini(system_prompt, user_content, temperature=0.4)
            if not payload:
                return None
            # Gemini may return a list instead of dict — normalise
            if isinstance(payload, list):
                payload = payload[0] if payload else {}
            if not isinstance(payload, dict):
                return None
            content = (payload.get("content") or "").strip()
            if not content:
                return None
            return content, payload.get("rationale") or "AI generated reply draft.", prompt_context
        except Exception:
            logger.exception("_ai_reply failed")
            return None

    def _ai_post(self, brand: BrandProfile | None, prompt_context: str) -> tuple[str, str, str] | None:
        try:
            system_prompt = "Return JSON with title, body, and rationale for a non-promotional Reddit post."
            user_content = json.dumps(
                {
                    "brand_name": brand.brand_name if brand else "",
                    "summary": brand.summary if brand else "",
                    "voice_notes": brand.voice_notes if brand else "",
                    "prompt_context": prompt_context,
                }
            )
            payload = self._call_gemini(system_prompt, user_content, temperature=0.5)
            if not payload:
                return None
            if isinstance(payload, list):
                payload = payload[0] if payload else {}
            if not isinstance(payload, dict):
                return None
            title = (payload.get("title") or "").strip()
            body = (payload.get("body") or "").strip()
            if not title or not body:
                return None
            return title, body, payload.get("rationale") or "AI generated post draft."
        except Exception:
            logger.exception("_ai_post failed")
            return None

    def _parse_json_payload(self, text: str) -> dict | list | None:
        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        decoder = json.JSONDecoder()
        candidates = [
            cleaned,
            cleaned[cleaned.find("{"):] if "{" in cleaned else "",
            cleaned[cleaned.find("["):] if "[" in cleaned else "",
        ]
        for candidate in candidates:
            candidate = candidate.strip()
            if not candidate:
                continue
            try:
                payload, _index = decoder.raw_decode(candidate)
                return payload
            except json.JSONDecodeError:
                continue
        return None
