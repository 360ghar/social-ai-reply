"""UTM parameter building and tracked-link code generation utilities."""

from __future__ import annotations

import secrets
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

LINK_CODE_BYTES = 6  # token_urlsafe(6) -> 8 URL-safe characters


def build_utm_params(
    project_slug: str,
    opportunity_id: int | None,
    platform: str = "reddit",
) -> dict[str, str]:
    """Build the standard UTM parameter set for a tracked link.

    Args:
        project_slug: Slug of the project, used as the campaign name.
        opportunity_id: When given, tags the link with ``utm_content=opp-{id}``.
        platform: Traffic source (defaults to ``reddit``).
    """
    params: dict[str, str] = {
        "utm_source": platform,
        "utm_medium": "community",
        "utm_campaign": project_slug,
    }
    if opportunity_id is not None:
        params["utm_content"] = f"opp-{opportunity_id}"
    return params


def append_utm(url: str, params: dict[str, str]) -> str:
    """Merge ``params`` into the URL's query string.

    Existing query parameters are preserved; parameters with the same key
    (e.g. pre-existing utm_* values) are overridden by ``params``. Values are
    decoded then re-encoded exactly once, so nothing gets double-encoded.
    """
    if not params:
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update({key: str(value) for key, value in params.items()})
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def generate_link_code() -> str:
    """Generate an 8-character URL-safe random link code."""
    return secrets.token_urlsafe(LINK_CODE_BYTES)
