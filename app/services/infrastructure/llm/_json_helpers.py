"""Shared JSON parsing utilities for LLM responses."""

from __future__ import annotations

import json
import re


def parse_json_payload(text: str) -> dict | list | None:
    """Parse JSON from LLM response text, handling markdown code blocks."""
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
