"""
JDIH normalizer — converts raw scraped HTML/dict into CivicStackResponse.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from civic_stack.shared.schema import CivicStackResponse, RecordStatus

logger = logging.getLogger(__name__)

MODULE = "jdih"

# Map Indonesian portal labels → normalized field names
_FIELD_MAP: dict[str, str] = {
    "judul": "title",
    "title": "title",
    "nomor": "regulation_number",
    "nomor peraturan": "regulation_number",
    "tahun": "year",
    "jenis": "document_type",
    "jenis dokumen": "document_type",
    "tentang": "subject",
    "subject": "subject",
    "tanggal penetapan": "issued_date",
    "tanggal": "issued_date",
    "pdf_url": "pdf_url",
    "url": "pdf_url",
}

_DATE_FORMATS = ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d %B %Y"]


def normalize_detail(
    raw: dict[str, str],
    *,
    doc_id: str,
    source_url: str,
    debug: bool = False,
) -> CivicStackResponse:
    """Parse a JDIH document detail into a CivicStackResponse."""
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
    
    # JDIH documents are generally ACTIVE if they appear in results
    status = RecordStatus.ACTIVE
    
    return CivicStackResponse(
        result=result,
        found=True,
        status=status,
        confidence=_confidence(raw, doc_id),
        source_url=source_url,
        fetched_at=datetime.utcnow(),
        module=MODULE,
        raw=raw if debug else None,
    )


def normalize_search_row(row: dict[str, str], *, source_url: str) -> CivicStackResponse:
    """Normalize a single row from a JDIH search results table."""
    result = _build_result(row)
    
    # JDIH documents are generally ACTIVE if they appear in results
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

    # Extract year from regulation number if present
    if "regulation_number" in result and "year" not in result:
        match = re.search(r"tahun\s+(\d{4})", result["regulation_number"], re.IGNORECASE)
        if match:
            result["year"] = match.group(1)

    # Parse issued date to ISO 8601 if present
    issued_str = result.get("issued_date")
    if issued_str:
        parsed = _parse_date(issued_str)
        if parsed:
            result["issued_date"] = parsed.isoformat()

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
    Confidence is 1.0 if the returned title/number matches the query
    (after normalizing), 0.9 otherwise.
    """
    title = raw.get("title", "")
    reg_no = raw.get("regulation_number", "")
    
    # Normalize: lowercase, remove extra whitespace
    def _norm(s: str) -> str:
        return re.sub(r"\s+", " ", s.lower().strip())

    query_norm = _norm(queried_id)
    title_norm = _norm(title)
    reg_norm = _norm(reg_no)
    
    return 1.0 if (query_norm in title_norm or query_norm in reg_norm) else 0.9
