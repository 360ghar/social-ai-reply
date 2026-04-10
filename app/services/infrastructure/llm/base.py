import json
from dataclasses import dataclass
from typing import Any, Protocol


class LLMProvider(Protocol):
    def generate_adjacent_personas(
        self,
        business_description: str,
        locale: str | None,
        max_personas: int,
    ) -> list[dict[str, Any]]:
        pass


@dataclass
class MockLLMProvider:
    def generate_adjacent_personas(
        self,
        business_description: str,
        locale: str | None,
        max_personas: int,
    ) -> list[dict[str, Any]]:
        desc = business_description.lower()
        region = locale or "target market"

        if "real estate" in desc or "property" in desc or "housing" in desc:
            base = [
                ("local realtors", "Realtor", "Same homebuyer and renter audience researching properties."),
                ("interior designers", "Interior Design Studio", "Same audience after home purchase or move-in."),
                ("mortgage brokers", "Mortgage Advisor", "Same audience in financing phase."),
                ("home staging companies", "Home Staging Service", "Same sellers trying to improve listing outcomes."),
                ("luxury home architects", "Architecture Firm", "Same premium property audience."),
                ("moving companies", "Relocation Service", "Same customer right after property transaction."),
                ("property photographers", "Real Estate Photography", "Same sellers and agents ecosystem."),
                ("home inspection services", "Home Inspector", "Same serious buyers in due diligence."),
                ("property lawyers", "Real Estate Legal Service", "Same buyers/sellers needing transaction support."),
                ("smart home installers", "Smart Home Integrator", "Same homeowners upgrading properties."),
            ]
        elif "fitness" in desc or "gym" in desc:
            base = [
                ("nutrition coaches", "Nutritionist", "Same audience focused on body transformation goals."),
                ("physiotherapists", "Physio Clinic", "Same active audience focused on injury prevention."),
                ("sportswear brands", "Athleisure Brand", "Same fitness-focused consumer segment."),
                ("yoga studios", "Yoga Studio", "Same wellness audience with overlapping intent."),
                ("meal prep services", "Healthy Meal Service", "Same customers managing fitness outcomes."),
            ]
        else:
            base = [
                ("local consultants", "Consulting Firm", "Likely adjacent decision-makers with overlapping budgets."),
                ("industry educators", "Training Provider", "Same audience seeking outcomes in the same domain."),
                ("tool reviewers", "Creator / Reviewer", "Same audience evaluating purchase options."),
                ("service agencies", "Agency", "Same customer base with adjacent service needs."),
                ("events and communities", "Community Organizer", "Same niche audience gathering in one place."),
                ("software integrators", "Implementation Partner", "Same audience needs tooling and onboarding."),
            ]

        personas: list[dict[str, Any]] = []
        for idx, (keyword, profile_type, reason) in enumerate(base[:max_personas], start=1):
            personas.append(
                {
                    "keyword": f"{keyword} {region}" if locale else keyword,
                    "profile_type": profile_type,
                    "overlap_reason": reason,
                    "priority_score": max(100 - idx * 6, 25),
                }
            )
        return personas


@dataclass
class GeminiLLMProvider:
    api_key: str
    model: str
    api_url: str = "https://generativelanguage.googleapis.com/v1beta"

    def generate_adjacent_personas(
        self,
        business_description: str,
        locale: str | None,
        max_personas: int,
    ) -> list[dict[str, Any]]:
        import httpx

        prompt = (
            "Generate adjacent, non-competing persona niches that share the same customer base. "
            f"Business: {business_description}. "
            f"Locale: {locale or 'not specified'}. "
            f"Return exactly {max_personas} items as JSON with key 'personas'. "
            "Each item must contain keyword, profile_type, overlap_reason, priority_score(1-100)."
        )
        url = f"{self.api_url}/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": "You are a precise GTM strategist.\n\n" + prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }
        resp = httpx.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
        parsed = json.loads(text)
        personas = parsed.get("personas", [])
        return [p for p in personas if isinstance(p, dict)]


def select_llm_provider(
    use_mock_llm: bool,
    gemini_api_key: str | None = None,
    gemini_model: str = "gemini-3-flash-preview",
    gemini_api_url: str = "https://generativelanguage.googleapis.com/v1beta",
    openai_api_key: str | None = None,
    openai_model: str = "gpt-4.1-mini",
) -> LLMProvider:
    if not use_mock_llm and gemini_api_key:
        return GeminiLLMProvider(api_key=gemini_api_key, model=gemini_model, api_url=gemini_api_url)
    return MockLLMProvider()
