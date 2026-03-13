"""
BPOM normalizer — converts raw scraped HTML/dict into CivicStackResponse.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from shared.schema import CivicStackResponse, RecordStatus, not_found_response

logger = logging.getLogger(__name__)

MODULE = "bpom"

# Map Indonesian portal labels → normalized field names
_FIELD_MAP: dict[str, str] = {
    "no. registrasi": "registration_no",
    "nomor registrasi": "registration_no",
    "nama produk": "product_name",
    "nama dagang": "brand_name",
    "jenis produk": "category",
    "nama pendaftar": "company",
    "alamat pendaftar": "company_address",
    "npwp": "company_npwp",
    "status registrasi": "registration_status",
    "tanggal kadaluarsa": "expiry_date",
    "tanggal awal berlaku": "valid_from",
}

# Indonesian status → RecordStatus
_STATUS_MAP: dict[str, RecordStatus] = {
    "aktif": RecordStatus.ACTIVE,
    "tidak aktif": RecordStatus.EXPIRED,
    "kadaluarsa": RecordStatus.EXPIRED,
    "dibatalkan": RecordStatus.REVOKED,
    "dibekukan": RecordStatus.SUSPENDED,
    "dicabut": RecordStatus.REVOKED,
}

_DATE_FORMATS = ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"]


def normalize_detail(
    soup: BeautifulSoup,
    *,
    registration_no: str,
    source_url: str,
    debug: bool = False,
) -> CivicStackResponse:
    """Parse a BPOM product detail page into a CivicStackResponse."""
    raw: dict[str, str] = _extract_detail_table(soup)

    if not raw or "registration_no" not in raw:
        return not_found_response(MODULE, source_url)

    result = _build_result(raw)
    status = _parse_status(raw.get("registration_status", ""))
    expiry = _parse_date(raw.get("expiry_date"))

    return CivicStackResponse(
        result=result,
        found=True,
        status=status,
        confidence=_confidence(raw, registration_no),
        source_url=source_url,
        fetched_at=datetime.utcnow(),
        last_updated=expiry,
        module=MODULE,
        raw=raw if debug else None,
    )


def normalize_search_row(row: dict[str, str], *, source_url: str) -> CivicStackResponse:
    """Normalize a single row from a BPOM search results table."""
    result = _build_result(row)
    status_str = row.get("status registrasi", row.get("status", ""))
    status = _parse_status(status_str)

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


def _extract_detail_table(soup: BeautifulSoup) -> dict[str, str]:
    """Extract key-value pairs from a BPOM detail page table."""
    data: dict[str, str] = {}

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower().rstrip(":")
                value = cells[1].get_text(strip=True)
                normalized_key = _FIELD_MAP.get(label)
                if normalized_key:
                    data[normalized_key] = value

    return data


def _build_result(raw: dict[str, Any]) -> dict[str, Any]:
    """Build the normalized result dict from raw field data."""
    result: dict[str, Any] = {}
    for src_key, dst_key in _FIELD_MAP.items():
        # raw may have normalized or raw keys
        val = raw.get(dst_key) or raw.get(src_key)
        if val:
            result[dst_key] = val

    # Normalize status string to our enum value
    status_raw = result.get("registration_status", "")
    result["registration_status"] = _parse_status(status_raw).value

    # Parse expiry date to ISO 8601 if present
    expiry_str = result.get("expiry_date")
    if expiry_str:
        parsed = _parse_date(expiry_str)
        if parsed:
            result["expiry_date"] = parsed.isoformat()

    return result


def _parse_status(status_str: str) -> RecordStatus:
    """Map an Indonesian status string to RecordStatus."""
    normalized = status_str.strip().lower()
    for key, val in _STATUS_MAP.items():
        if key in normalized:
            return val
    return RecordStatus.NOT_FOUND if not normalized else RecordStatus.ACTIVE


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


def _confidence(raw: dict[str, str], queried_no: str) -> float:
    """
    Confidence is 1.0 if the returned registration_no matches the query
    (after stripping whitespace and normalizing case), 0.9 otherwise.
    """
    returned_no = raw.get("registration_no", "")
    # Normalize: remove spaces, uppercase
    def _norm(s: str) -> str:
        return re.sub(r"\s+", "", s).upper()

    return 1.0 if _norm(returned_no) == _norm(queried_no) else 0.9
