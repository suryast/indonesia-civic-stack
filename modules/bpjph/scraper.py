"""
BPJPH Halal Certificate scraper — REST API-based.

Source: cmsbl.halal.go.id (primary), gateway.halal.go.id (fallback)
Method: httpx REST API (no browser/Playwright needed)
License: Apache-2.0

Public API:
    fetch(cert_no, *, debug=False, proxy_url=None) -> CivicStackResponse
    search(keyword, *, proxy_url=None) -> list[CivicStackResponse]
    cross_ref_bpom(product_name, *, proxy_url=None) -> dict
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from civic_stack.shared.http import civic_client
from civic_stack.shared.schema import CivicStackResponse, RecordStatus, not_found_response

logger = logging.getLogger(__name__)

MODULE = "bpjph"

# API endpoints discovered from bpjph.halal.go.id frontend JS
CMSBL_BASE = "https://cmsbl.halal.go.id"
SEARCH_URL = f"{CMSBL_BASE}/api/search"
GATEWAY_BASE = "https://gateway.halal.go.id"

# Search types supported by cmsbl API
SEARCH_TYPE_PRODUCT = "data_produk"
SEARCH_TYPE_COMPANY = "data_penyelia"
SEARCH_TYPE_CERT = "data_sertifikat"

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


async def fetch(
    cert_no: str,
    *,
    debug: bool = False,
    proxy_url: str | None = None,
) -> CivicStackResponse:
    """Fetch a halal certificate by certificate number."""
    source_url = f"{SEARCH_URL}/{SEARCH_TYPE_CERT}?no_sertifikat={cert_no}"

    async with civic_client(proxy_url=proxy_url) as client:
        try:
            resp = await client.get(
                f"{SEARCH_URL}/{SEARCH_TYPE_CERT}",
                params={"no_sertifikat": cert_no},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("BPJPH fetch failed for %s: %s", cert_no, e)
            return not_found_response(MODULE, source_url)

    records = _extract_records(data)
    if not records:
        return not_found_response(MODULE, source_url)

    # Find exact match
    record = records[0]
    for r in records:
        if r.get("no_sertifikat", "").strip().upper() == cert_no.strip().upper():
            record = r
            break

    result = _normalize_record(record)
    status = _parse_status(record.get("status_sertifikat", ""))
    confidence = (
        1.0 if record.get("no_sertifikat", "").strip().upper() == cert_no.strip().upper() else 0.9
    )

    return CivicStackResponse(
        result=result,
        found=True,
        status=status,
        confidence=confidence,
        source_url=source_url,
        fetched_at=datetime.utcnow(),
        module=MODULE,
        raw=record if debug else None,
    )


async def search(
    keyword: str,
    *,
    search_type: str = SEARCH_TYPE_PRODUCT,
    proxy_url: str | None = None,
) -> list[CivicStackResponse]:
    """Search halal certificates by product name, company, or cert number."""
    param_key = _param_key_for_type(search_type)
    source_url = f"{SEARCH_URL}/{search_type}?{param_key}={keyword}"

    async with civic_client(proxy_url=proxy_url) as client:
        try:
            resp = await client.get(
                f"{SEARCH_URL}/{search_type}",
                params={param_key: keyword},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("BPJPH search failed for %s: %s", keyword, e)
            return [not_found_response(MODULE, source_url)]

    records = _extract_records(data)
    if not records:
        return [not_found_response(MODULE, source_url)]

    results = []
    for record in records:
        result = _normalize_record(record)
        status = _parse_status(record.get("status_sertifikat", ""))
        results.append(
            CivicStackResponse(
                result=result,
                found=True,
                status=status,
                confidence=0.8,
                source_url=source_url,
                fetched_at=datetime.utcnow(),
                module=MODULE,
            )
        )
    return results


async def cross_ref_bpom(
    product_name: str,
    *,
    proxy_url: str | None = None,
) -> dict[str, Any]:
    """Cross-reference a product between BPJPH halal and BPOM databases."""
    halal_results = await search(product_name, proxy_url=proxy_url)

    try:
        from civic_stack.bpom.scraper import search as bpom_search

        bpom_results = await bpom_search(product_name, proxy_url=proxy_url)
    except Exception:
        bpom_results = []

    return {
        "product": product_name,
        "halal_found": any(r.found for r in halal_results),
        "bpom_found": any(r.found for r in bpom_results),
        "halal_results": len([r for r in halal_results if r.found]),
        "bpom_results": len([r for r in bpom_results if r.found]),
    }


# ── Private helpers ───────────────────────────────────────────────────────────


def _param_key_for_type(search_type: str) -> str:
    """Map search type to the correct query parameter name."""
    return {
        SEARCH_TYPE_PRODUCT: "nama",
        SEARCH_TYPE_COMPANY: "nama_penyelia",
        SEARCH_TYPE_CERT: "no_sertifikat",
    }.get(search_type, "nama")


def _extract_records(data: Any) -> list[dict]:
    """Extract records from API response (handles various response shapes)."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "results", "records", "items"):
            if key in data and isinstance(data[key], list):
                return data[key]
        # Some responses nest under data.data
        if "data" in data and isinstance(data["data"], dict):
            inner = data["data"]
            for key in ("data", "results", "records"):
                if key in inner and isinstance(inner[key], list):
                    return inner[key]
    return []


def _normalize_record(record: dict) -> dict[str, Any]:
    """Normalize a raw API record to our standard result shape."""
    result: dict[str, Any] = {}

    # Map common field names
    field_map = {
        "no_sertifikat": "cert_no",
        "nomor_sertifikat": "cert_no",
        "nama_perusahaan": "company",
        "nama_pelaku_usaha": "company",
        "nama_produk": "product_list",
        "produk": "product_list",
        "penerbit": "issuer",
        "lembaga_pemeriksa": "inspection_body",
        "tgl_terbit": "issue_date",
        "tanggal_terbit": "issue_date",
        "tgl_kadaluarsa": "expiry_date",
        "tanggal_kadaluarsa": "expiry_date",
        "masa_berlaku": "expiry_date",
        "status_sertifikat": "status",
        "status": "status",
    }

    for raw_key, norm_key in field_map.items():
        val = record.get(raw_key)
        if val and norm_key not in result:
            result[norm_key] = val

    # Set issuer default
    if "issuer" not in result:
        result["issuer"] = "BPJPH"

    # Normalize product_list to a list
    if "product_list" in result and isinstance(result["product_list"], str):
        import re

        products = re.split(r"[,\n;]+", result["product_list"])
        result["product_list"] = [p.strip() for p in products if p.strip()]

    # Normalize status to enum value
    if "status" in result:
        result["status"] = _parse_status(str(result["status"])).value

    return result


def _parse_status(status_str: str) -> RecordStatus:
    """Parse Indonesian status string to RecordStatus enum."""
    normalized = status_str.strip().lower()
    for key, val in _STATUS_MAP.items():
        if key in normalized:
            return val
    return RecordStatus.NOT_FOUND if not normalized else RecordStatus.ACTIVE
