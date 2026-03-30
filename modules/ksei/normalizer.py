"""
KSEI normalizer — converts raw scraped HTML/dict into CivicStackResponse.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from civic_stack.shared.schema import CivicStackResponse, RecordStatus

logger = logging.getLogger(__name__)

MODULE = "ksei"

# Map common field labels → normalized field names
_FIELD_MAP: dict[str, str] = {
    "periode": "period",
    "period": "period",
    "bulan": "month",
    "month": "month",
    "tahun": "year",
    "year": "year",
    "judul": "title",
    "title": "title",
    "kategori": "category",
    "category": "category",
    "nilai": "value",
    "value": "value",
    "jumlah": "total",
    "total": "total",
    "download_url": "download_url",
    "url": "download_url",
}

_DATE_FORMATS = ["%B %Y", "%m/%Y", "%Y-%m", "%d-%m-%Y", "%d/%m/%Y"]


def normalize_detail(
    raw: dict[str, str],
    *,
    report_id: str,
    source_url: str,
    debug: bool = False,
) -> CivicStackResponse:
    """Parse a KSEI report detail into a CivicStackResponse."""
    if not raw:
        return CivicStackResponse(
            result=None,
            found=False,
            status=RecordStatus.NOT_FOUND,
            confidence=0.0,
            source_url=source_url,
            fetched_at=datetime.utcnow(),
            module=MODULE,
        )

    result = _build_result(raw)
    
    # KSEI statistics are generally ACTIVE
    status = RecordStatus.ACTIVE
    
    return CivicStackResponse(
        result=result,
        found=True,
        status=status,
        confidence=_confidence(raw, report_id),
        source_url=source_url,
        fetched_at=datetime.utcnow(),
        module=MODULE,
        raw=raw if debug else None,
    )


def normalize_search_row(row: dict[str, str], *, source_url: str) -> CivicStackResponse:
    """Normalize a single row from a KSEI search results."""
    result = _build_result(row)
    
    # KSEI statistics are generally ACTIVE
    status = RecordStatus.ACTIVE

    return CivicStackResponse(
        result=result,
        found=True,
        status=status,
        confidence=0.8,  # search results are less certain than direct lookups
        source_url=source_url,
        fetched_at=datetime.utcnow(),
        module=MODULE,
    )


# ── Private helpers ───────────────────────────────────────────────────────────


def _build_result(raw: dict[str, Any]) -> dict[str, Any]:
    """Build the normalized result dict from raw field data."""
    result: dict[str, Any] = {}
    
    for src_key, dst_key in _FIELD_MAP.items():
        # raw may have normalized or raw keys
        val = raw.get(dst_key) or raw.get(src_key)
        if val:
            result[dst_key] = val

    # Parse period date to ISO 8601 if present
    period_str = result.get("period")
    if period_str:
        parsed = _parse_date(period_str)
        if parsed:
            result["period_date"] = parsed.isoformat()

    return result


def _parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    logger.debug("Could not parse date string: %s", date_str)
    return None


def _confidence(raw: dict[str, str], queried_id: str) -> float:
    """
    Confidence is 1.0 if the returned title/period matches the query
    (after normalizing), 0.9 otherwise.
    """
    title = raw.get("title", "")
    period = raw.get("period", "")
    
    # Normalize: lowercase, remove extra whitespace
    def _norm(s: str) -> str:
        return re.sub(r"\s+", " ", s.lower().strip())

    query_norm = _norm(queried_id)
    title_norm = _norm(title)
    period_norm = _norm(period)
    
    return 1.0 if (query_norm in title_norm or query_norm in period_norm) else 0.9
