"""
AHU normalizer — converts raw Playwright-rendered HTML into CivicStackResponse.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from shared.schema import CivicStackResponse, RecordStatus, not_found_response

logger = logging.getLogger(__name__)

MODULE = "ahu"

_STATUS_MAP: dict[str, RecordStatus] = {
    "aktif": RecordStatus.ACTIVE,
    "terdaftar": RecordStatus.ACTIVE,
    "berlaku": RecordStatus.ACTIVE,
    "bubar": RecordStatus.REVOKED,
    "pembubaran": RecordStatus.REVOKED,
    "pailit": RecordStatus.SUSPENDED,
    "dibekukan": RecordStatus.SUSPENDED,
    "tidak aktif": RecordStatus.EXPIRED,
    "dicabut": RecordStatus.REVOKED,
}

_LEGAL_FORMS = {"PT", "CV", "Firma", "Koperasi", "Yayasan", "Perkumpulan", "UD"}

_DATE_FORMATS = ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d %B %Y"]
_ID_MONTHS = {
    "januari": "01", "februari": "02", "maret": "03", "april": "04",
    "mei": "05", "juni": "06", "juli": "07", "agustus": "08",
    "september": "09", "oktober": "10", "november": "11", "desember": "12",
}

# Field label → normalized key
_FIELD_MAP: dict[str, str] = {
    "nama perusahaan": "company_name",
    "nama pt": "company_name",
    "nomor akta": "deed_no",
    "nomor pengesahan": "registration_no",
    "tanggal pengesahan": "deed_date",
    "tanggal akta": "deed_date",
    "tanggal berdiri": "established_date",
    "status": "legal_status",
    "status perusahaan": "legal_status",
    "bentuk badan usaha": "legal_form",
    "jenis perseroan": "legal_form",
    "domisili": "domicile",
    "alamat": "domicile",
    "kegiatan usaha": "business_activities",
    "maksud dan tujuan": "business_activities",
    "modal dasar": "authorized_capital",
    "modal disetor": "paid_up_capital",
}


def normalize_company_page(
    html: str,
    *,
    query: str,
    source_url: str,
    debug: bool = False,
) -> CivicStackResponse:
    """Parse an AHU company detail page into a CivicStackResponse."""
    soup = BeautifulSoup(html, "html.parser")
    raw = _extract_company_fields(soup)
    directors = _extract_directors(soup)
    commissioners = _extract_commissioners(soup)

    if not raw or "company_name" not in raw:
        return not_found_response(MODULE, source_url)

    result = _build_result(raw, directors, commissioners)
    status = _parse_status(raw.get("legal_status", ""))

    return CivicStackResponse(
        result=result,
        found=True,
        status=status,
        confidence=_confidence(raw, query),
        source_url=source_url,
        fetched_at=datetime.utcnow(),
        last_updated=_parse_date(raw.get("deed_date")),
        module=MODULE,
        raw={**raw, "directors": directors, "commissioners": commissioners} if debug else None,
    )


def normalize_search_results(html: str, *, source_url: str) -> list[CivicStackResponse]:
    """Parse an AHU search results table."""
    soup = BeautifulSoup(html, "html.parser")
    rows = _extract_table_rows(soup)

    if not rows:
        return [not_found_response(MODULE, source_url)]

    results = []
    for row in rows:
        status = _parse_status(row.get("status", row.get("status perusahaan", "")))
        result = {
            "company_name": row.get("nama perusahaan", row.get("nama pt", "")),
            "registration_no": row.get("nomor pengesahan", ""),
            "legal_form": row.get("bentuk badan usaha", row.get("jenis perseroan", "")),
            "legal_status": status.value,
            "domicile": row.get("domisili", row.get("alamat", "")),
        }
        results.append(
            CivicStackResponse(
                result={k: v for k, v in result.items() if v},
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


def _extract_company_fields(soup: BeautifulSoup) -> dict[str, str]:
    data: dict[str, str] = {}
    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True).lower().rstrip(":")
            value = cells[1].get_text(strip=True)
            mapped = _FIELD_MAP.get(label)
            if mapped and value:
                data[mapped] = value
    # Also try definition-list layouts (newer React portals)
    for dl in soup.find_all("dl"):
        for dt, dd in zip(dl.find_all("dt"), dl.find_all("dd")):
            label = dt.get_text(strip=True).lower()
            value = dd.get_text(strip=True)
            mapped = _FIELD_MAP.get(label)
            if mapped and value:
                data[mapped] = value
    return data


def _extract_directors(soup: BeautifulSoup) -> list[dict[str, str]]:
    """Extract director (Direksi) list from the company detail page."""
    directors: list[dict[str, str]] = []
    # Look for a section or table headed with "Direksi"
    for heading in soup.find_all(["h3", "h4", "th", "td", "div"], string=re.compile(r"[Dd]ireksi")):
        table = heading.find_next("table")
        if table:
            directors = _parse_person_table(table)
            break
    return directors


def _extract_commissioners(soup: BeautifulSoup) -> list[dict[str, str]]:
    """Extract commissioner (Dewan Komisaris) list."""
    commissioners: list[dict[str, str]] = []
    for heading in soup.find_all(
        ["h3", "h4", "th", "td", "div"],
        string=re.compile(r"[Kk]omisaris"),
    ):
        table = heading.find_next("table")
        if table:
            commissioners = _parse_person_table(table)
            break
    return commissioners


def _parse_person_table(table: Any) -> list[dict[str, str]]:
    """Parse a table of directors or commissioners."""
    people: list[dict[str, str]] = []
    headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all("td")
        if not cells:
            continue
        person = {headers[i]: cells[i].get_text(strip=True) for i in range(min(len(headers), len(cells)))}
        if person:
            people.append(person)
    return people


def _extract_table_rows(soup: BeautifulSoup) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    table = soup.find("table")
    if not table:
        return rows
    headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all("td")
        if not cells:
            continue
        rows.append({headers[i]: cells[i].get_text(strip=True) for i in range(min(len(headers), len(cells)))})
    return rows


def _build_result(
    raw: dict[str, str],
    directors: list[dict[str, str]],
    commissioners: list[dict[str, str]],
) -> dict[str, Any]:
    result: dict[str, Any] = {k: v for k, v in raw.items() if v}
    result["legal_status"] = _parse_status(raw.get("legal_status", "")).value
    if directors:
        result["directors"] = directors
    if commissioners:
        result["commissioners"] = commissioners
    # Parse deed_date to ISO 8601
    if raw.get("deed_date"):
        parsed = _parse_date(raw["deed_date"])
        if parsed:
            result["deed_date"] = parsed.isoformat()
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
    s = date_str.strip().lower()
    for id_m, num in _ID_MONTHS.items():
        s = s.replace(id_m, num)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _confidence(raw: dict[str, str], query: str) -> float:
    company_name = raw.get("company_name", "").upper()
    query_upper = query.upper()
    if company_name == query_upper:
        return 1.0
    if query_upper in company_name or company_name in query_upper:
        return 0.9
    return 0.7
