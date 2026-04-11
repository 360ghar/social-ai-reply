"""Inference helpers for extracting audience, CTA, and business domain from text."""


def infer_audience(summary: str) -> str:
    """Infer target audience from summary text."""
    lowered = summary.lower()
    if "developer" in lowered or "engineering" in lowered:
        return "developers, engineering leaders, technical founders"
    if "marketing" in lowered or "growth" in lowered:
        return "founders, growth marketers, demand gen teams"
    if "sales" in lowered:
        return "founders, sales leaders, revenue teams"
    return "founders, operators, marketing teams"


def infer_cta(summary: str) -> str:
    """Infer call-to-action from summary text."""
    if "book" in summary.lower() or "demo" in summary.lower():
        return "Invite interested users to ask for the process or request a demo."
    return "Offer a useful next step only if the conversation naturally asks for it."


def infer_business_domain(summary: str, description: str = "") -> str:
    """Infer business domain from summary and description text."""
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
