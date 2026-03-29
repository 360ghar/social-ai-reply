import json
import logging
import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.db.saas_models import BrandProfile, Opportunity, Persona, PromptTemplate

logger = logging.getLogger(__name__)


@dataclass
class WebsiteAnalysis:
    brand_name: str
    summary: str
    product_summary: str
    target_audience: str
    call_to_action: str
    voice_notes: str


@dataclass
class GeneratedKeyword:
    keyword: str
    rationale: str
    priority_score: int


class ProductCopilot:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.gemini_api_key or settings.openai_api_key
        self.use_ai = bool(self.api_key) and "PYTEST_CURRENT_TEST" not in os.environ
        self.model = settings.gemini_model or "gemini-2-flash-preview"
        self.api_url = settings.gemini_api_url or "https://generativelanguage.googleapis.com/v1beta"
        self.user_agent = settings.reddit_user_agent

    def analyze_website(self, website_url: str) -> WebsiteAnalysis:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            response = client.get(website_url, headers={"User-Agent": self.user_agent})
            response.raise_for_status()
        html = response.text
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
        )

    def suggest_personas(self, brand: BrandProfile | None, count: int = 4) -> list[dict]:
        seed = (brand.target_audience if brand and brand.target_audience else "founders, marketers, operators").split(",")
        personas = []
        for idx, base in enumerate(seed[:count], start=1):
            label = base.strip().title() or f"Persona {idx}"
            personas.append(
                {
                    "name": label,
                    "role": label,
                    "summary": f"{label} looks for practical ways to improve outcomes with minimal fluff.",
                    "pain_points": ["Wants signal over noise", "Needs trustworthy proof", "Avoids spammy vendors"],
                    "goals": ["Find repeatable growth channels", "Learn from peer examples"],
                    "triggers": ["New problem appears", "Current channel underperforms"],
                    "preferred_subreddits": [],
                    "source": "generated",
                }
            )
        return personas

    def generate_keywords(self, brand: BrandProfile | None, personas: list[Persona], count: int = 12) -> list[GeneratedKeyword]:
        if not brand:
            return []
        seed_parts = [
            brand.brand_name,
            brand.product_summary or "",
            brand.target_audience or "",
            brand.summary or "",
            " ".join(persona.name for persona in personas[:5]),
        ]
        corpus = " ".join(seed_parts)
        tokens = self._meaningful_terms(corpus)
        phrases = []
        if brand.brand_name:
            phrases.append((brand.brand_name.lower(), "Brand name monitoring for direct mentions.", 95))
        for token in tokens:
            phrases.append((token, f"Derived from the brand and persona context around {token}.", max(85 - len(phrases) * 4, 40)))
        deduped: list[GeneratedKeyword] = []
        seen: set[str] = set()
        for keyword, rationale, score in phrases:
            normalized = keyword.strip().lower()
            if len(normalized) < 3 or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(GeneratedKeyword(keyword=normalized, rationale=rationale, priority_score=score))
            if len(deduped) >= count:
                break
        return deduped

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
            f"You're not the only one dealing with this. A practical way to approach it is to start with the constraint "
            f"that is slowing progress the most, test one small fix, and compare the before/after signal. "
            f"We've seen teams similar to yours benefit from documenting what changed and why before expanding the solution."
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
        return title, body, prompt_context

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
            return json.loads(text)
        except Exception:
            logger.exception("Gemini API call failed")
            return None

    def _structured_brand_analysis(self, text: str, fallback_name: str) -> WebsiteAnalysis | None:
        try:
            system_prompt = (
                "You extract go-to-market context for a Reddit engagement platform. "
                "Return JSON with brand_name, summary, product_summary, target_audience, call_to_action, voice_notes."
            )
            payload = self._call_gemini(system_prompt, text[:12000], temperature=0.2)
            if not payload:
                return None
            return WebsiteAnalysis(
                brand_name=payload.get("brand_name") or fallback_name,
                summary=payload.get("summary") or text[:280],
                product_summary=payload.get("product_summary") or text[:280],
                target_audience=payload.get("target_audience") or self._infer_audience(text),
                call_to_action=payload.get("call_to_action") or self._infer_cta(text),
                voice_notes=payload.get("voice_notes") or "Helpful, grounded, and specific.",
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
                "Write a useful Reddit reply. Avoid spam, avoid sounding salesy, do not mention the company unless asked. "
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
            title = (payload.get("title") or "").strip()
            body = (payload.get("body") or "").strip()
            if not title or not body:
                return None
            return title, body, payload.get("rationale") or "AI generated post draft."
        except Exception:
            logger.exception("_ai_post failed")
            return None
