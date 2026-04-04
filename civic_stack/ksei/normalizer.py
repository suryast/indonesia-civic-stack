"""KSEI normalizer — maps scraped HTML to canonical fields."""

from __future__ import annotations

from typing import Any

_SECURITY_MAP: dict[str, str] = {
    "security_code": "security_code",
    "security_name": "security_name",
    "security_type": "security_type",
    "issuer": "issuer",
    "status": "status",
}

_STATISTICS_MAP: dict[str, str] = {
    "period": "statistics_period",
    "month": "month",
    "year": "year",
    "download_url": "download_url",
}


def normalize_security(raw: dict[str, Any]) -> dict[str, Any]:
    """Map scraped security data to canonical schema."""
    out: dict[str, Any] = {}
    for src, dst in _SECURITY_MAP.items():
        val = raw.get(src)
        if val is not None and val != "":
            out[dst] = val
    return out


def normalize_statistics_link(raw: dict[str, Any]) -> dict[str, Any]:
    """Map scraped statistics link data to canonical schema."""
    out: dict[str, Any] = {}
    for src, dst in _STATISTICS_MAP.items():
        val = raw.get(src)
        if val is not None and val != "":
            out[dst] = val
    return out
