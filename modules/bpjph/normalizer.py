"""
BPJPH normalizer — converts raw Playwright-rendered HTML into CivicStackResponse.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from shared.schema import CivicStackResponse, RecordStatus, not_found_response

logger = logging.getLogger(__name__)

MODULE = "bpjph"

_STATUS_MAP: dict[str, RecordStatus] = {
    "berlaku": RecordStatus.ACTIVE,
    "aktif": RecordStatus.ACTIVE,
    "valid": RecordStatus.ACTIVE,
    "kadaluarsa": RecordStatus.EXPIRED,
    "expired": RecordStatus.EXPIRED,
    "tidak berlaku": RecordStatus.EXPIRED,
    "dicabut": RecordStatus.REVOKED,
    "revoked": RecordStatus.REVOKED,
    "dibekukan": RecordStatus.SUSPENDED,
    "suspended": RecordStatus.SUSPENDED,
}

_DATE_FORMATS = ["%d %B %Y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"]

# Indonesian month names → numbers
_ID_MONTHS = {
    "januari": "01",
    "februari": "02",
    "maret": "03",
    "april": "04",
    "mei": "05",
    "juni": "06",
    "juli": "07",
    "agustus": "08",
    "september": "09",
    "oktober": "10",
    "november": "11",
    "desember": "12",
}


def normalize_cert_page(
    html: str,
    *,
    cert_no: str,
    source_url: str,
    debug: bool = False,
) -> CivicStackResponse:
    """Parse a BPJPH certificate detail page."""
    soup = BeautifulSoup(html, "html.parser")
    raw = _extract_cert_fields(soup)

    if not raw:
        return not_found_response(MODULE, source_url)

    result = _build_result(raw)
    status = _parse_status(raw.get("status", ""))
    expiry = _parse_date(raw.get("expiry_date"))

    return CivicStackResponse(
        result=result,
        found=True,
        status=status,
        confidence=_confidence(raw, cert_no),
        source_url=source_url,
        fetched_at=datetime.utcnow(),
        last_updated=expiry,
        module=MODULE,
        raw=raw if debug else None,
    )


def normalize_search_results(html: str, *, source_url: str) -> list[CivicStackResponse]:
    """Parse a BPJPH search results page into a list of CivicStackResponse."""
    soup = BeautifulSoup(html, "html.parser")
    rows = _extract_table_rows(soup)

    if not rows:
        return [not_found_response(MODULE, source_url)]

    results = []
    for row in rows:
        status = _parse_status(row.get("status", ""))
        results.append(
            CivicStackResponse(
                result=_build_result(row),
                found=True,
                status=status,
                confidence=0.8,
                source_url=source_url,
                fetched_at=datetime.utcnow(),
                module=MODULE,
            )
        )
    return results


# ── Private helpers ───────────────────────────────────────────────────────────


def _extract_cert_fields(soup: BeautifulSoup) -> dict[str, str]:
    """Extract certificate fields from a detail page."""
    data: dict[str, str] = {}

    # Try table-based layout (th/td pairs)
    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True).lower()
            value = cells[1].get_text(strip=True)
            _store_field(data, label, value)

    # Try definition-list or labeled-div layout (common in React portals)
    for label_el in soup.find_all(["dt", "label", "span"], class_=re.compile(r"label|key|title")):
        label = label_el.get_text(strip=True).lower()
        value_el = label_el.find_next_sibling(["dd", "span", "p"])
        if value_el:
            _store_field(data, label, value_el.get_text(strip=True))

    return data


def _store_field(data: dict[str, str], label: str, value: str) -> None:
    """Map a raw label/value pair to a normalized field name."""
    label = label.rstrip(":").strip()
    mappings = {
        "nomor sertifikat": "cert_no",
        "no. sertifikat": "cert_no",
        "no sertifikat": "cert_no",
        "nama perusahaan": "company",
        "nama produk": "product_list",
        "produk": "product_list",
        "penerbit": "issuer",
        "lembaga pemeriksa": "inspection_body",
        "tanggal terbit": "issue_date",
        "tanggal berlaku": "issue_date",
        "tanggal kadaluarsa": "expiry_date",
        "berlaku sampai": "expiry_date",
        "masa berlaku": "expiry_date",
        "status": "status",
        "status sertifikat": "status",
    }
    mapped = mappings.get(label)
    if mapped and value:
        data[mapped] = value


def _extract_table_rows(soup: BeautifulSoup) -> list[dict[str, str]]:
    """Extract rows from a search results table."""
    rows: list[dict[str, str]] = []
    table = soup.find("table")
    if not table:
        return rows

    headers: list[str] = [th.get_text(strip=True).lower() for th in table.find_all("th")]
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all("td")
        if not cells:
            continue
        row: dict[str, str] = {}
        for i, cell in enumerate(cells):
            if i < len(headers):
                row[headers[i]] = cell.get_text(strip=True)
        rows.append(row)
    return rows


def _build_result(raw: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in (
        "cert_no",
        "company",
        "product_list",
        "issuer",
        "inspection_body",
        "issue_date",
        "expiry_date",
        "status",
    ):
        if raw.get(key):
            result[key] = raw[key]

    # Normalize status to enum value
    result["status"] = _parse_status(raw.get("status", "")).value

    # Convert product_list to a proper list if comma/newline separated
    if "product_list" in result:
        products = re.split(r"[,\n;]+", result["product_list"])
        result["product_list"] = [p.strip() for p in products if p.strip()]

    return result


def _parse_status(status_str: str) -> RecordStatus:
    normalized = status_str.strip().lower()
    for key, val in _STATUS_MAP.items():
        if key in normalized:
            return val
    return RecordStatus.NOT_FOUND if not normalized else RecordStatus.ACTIVE


def _parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    # Normalize Indonesian month names
    s = date_str.strip().lower()
    for id_month, num in _ID_MONTHS.items():
        s = s.replace(id_month, num)

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s.title() if "%B" in fmt else s, fmt)
        except ValueError:
            continue
    return None


def _confidence(raw: dict[str, str], queried_cert_no: str) -> float:
    returned = re.sub(r"\s+", "", raw.get("cert_no", "")).upper()
    queried = re.sub(r"\s+", "", queried_cert_no).upper()
    return 1.0 if returned == queried else 0.9
