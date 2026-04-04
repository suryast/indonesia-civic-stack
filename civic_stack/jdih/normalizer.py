"""JDIH normalizer — maps scraped HTML to canonical fields."""

from __future__ import annotations

from typing import Any

_REGULATION_MAP: dict[str, str] = {
    "regulation_id": "regulation_id",
    "regulation_type": "regulation_type",
    "number": "number",
    "year": "year",
    "title": "title",
    "status": "status",
    "about": "about",
    "full_url": "full_url",
}


def normalize_regulation(raw: dict[str, Any]) -> dict[str, Any]:
    """Map scraped regulation data to canonical schema."""
    out: dict[str, Any] = {}
    for src, dst in _REGULATION_MAP.items():
        val = raw.get(src)
        if val is not None and val != "":
            out[dst] = val
    return out
