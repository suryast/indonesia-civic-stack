"""OSS-NIB normalizer — Playwright-rendered HTML → CivicStackResponse."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup

from shared.schema import CivicStackResponse, RecordStatus, not_found_response

MODULE = "oss_nib"

_STATUS_MAP = {
    "aktif": RecordStatus.ACTIVE,
    "berlaku": RecordStatus.ACTIVE,
    "tidak aktif": RecordStatus.EXPIRED,
    "dicabut": RecordStatus.REVOKED,
    "dibekukan": RecordStatus.SUSPENDED,
}

_RISK_LEVELS = {"rendah", "menengah rendah", "menengah tinggi", "tinggi"}

_FIELD_MAP = {
    "nib": "nib",
    "nomor induk berusaha": "nib",
    "nama perusahaan": "company_name",
    "nama usaha": "company_name",
    "jenis usaha": "business_type",
    "kbli": "kbli_code",
    "klasifikasi baku lapangan usaha": "kbli_code",
    "tingkat risiko": "risk_level",
    "status": "license_status",
    "status usaha": "license_status",
    "domisili": "domicile",
    "alamat": "domicile",
    "tanggal terbit": "issue_date",
    "tanggal nib": "issue_date",
}


def normalize_nib_page(
    html: str,
    *,
    query: str,
    source_url: str,
    debug: bool = False,
) -> CivicStackResponse:
    soup = BeautifulSoup(html, "html.parser")
    raw = _extract_fields(soup)

    if not raw or "nib" not in raw:
        return not_found_response(MODULE, source_url)

    result = _build_result(raw)
    status = _parse_status(raw.get("license_status", ""))

    return CivicStackResponse(
        result=result,
        found=True,
        status=status,
        confidence=_confidence(raw, query),
        source_url=source_url,
        fetched_at=datetime.now(UTC),
        module=MODULE,
        raw=raw if debug else None,
    )


def normalize_search_results(html: str, *, source_url: str) -> list[CivicStackResponse]:
    soup = BeautifulSoup(html, "html.parser")
    rows = _extract_table_rows(soup)
    if not rows:
        return [not_found_response(MODULE, source_url)]

    results = []
    for row in rows:
        status = _parse_status(row.get("status usaha", row.get("status", "")))
        result: dict[str, Any] = {
            "nib": row.get("nib", ""),
            "company_name": row.get("nama perusahaan", row.get("nama usaha", "")),
            "business_type": row.get("jenis usaha", ""),
            "risk_level": row.get("tingkat risiko", ""),
            "license_status": status.value,
            "domicile": row.get("domisili", row.get("alamat", "")),
        }
        results.append(
            CivicStackResponse(
                result={k: v for k, v in result.items() if v},
                found=True,
                status=status,
                confidence=0.8,
                source_url=source_url,
                fetched_at=datetime.now(UTC),
                module=MODULE,
            )
        )
    return results


def _extract_fields(soup: BeautifulSoup) -> dict[str, str]:
    data: dict[str, str] = {}
    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True).lower().rstrip(":")
            value = cells[1].get_text(strip=True)
            mapped = _FIELD_MAP.get(label)
            if mapped and value:
                data[mapped] = value
    for dl in soup.find_all("dl"):
        for dt, dd in zip(dl.find_all("dt"), dl.find_all("dd"), strict=False):
            label = dt.get_text(strip=True).lower()
            value = dd.get_text(strip=True)
            mapped = _FIELD_MAP.get(label)
            if mapped and value:
                data[mapped] = value
    return data


def _extract_table_rows(soup: BeautifulSoup) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    table = soup.find("table")
    if not table:
        return rows
    headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all("td")
        if cells:
            rows.append(
                {
                    headers[i]: cells[i].get_text(strip=True)
                    for i in range(min(len(headers), len(cells)))
                }
            )
    return rows


def _build_result(raw: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = dict(raw)
    result["license_status"] = _parse_status(raw.get("license_status", "")).value
    return result


def _parse_status(s: str) -> RecordStatus:
    n = s.strip().lower()
    for k, v in _STATUS_MAP.items():
        if k in n:
            return v
    return RecordStatus.ACTIVE if n else RecordStatus.NOT_FOUND


def _confidence(raw: dict[str, str], query: str) -> float:
    nib = raw.get("nib", "")
    name = raw.get("company_name", "").upper()
    query_up = query.upper()
    if nib == query or name == query_up:
        return 1.0
    if query_up in name or (nib and nib in query):
        return 0.9
    return 0.8
