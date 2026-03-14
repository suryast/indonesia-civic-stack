"""OJK normalizer — API/scraped data → CivicStackResponse."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from civic_stack.shared.schema import CivicStackResponse, RecordStatus

MODULE = "ojk"

_STATUS_MAP = {
    "aktif": RecordStatus.ACTIVE,
    "izin usaha": RecordStatus.ACTIVE,
    "beroperasi": RecordStatus.ACTIVE,
    "dicabut": RecordStatus.REVOKED,
    "pembekuan": RecordStatus.SUSPENDED,
    "dibekukan": RecordStatus.SUSPENDED,
    "likuidasi": RecordStatus.REVOKED,
    "tidak aktif": RecordStatus.EXPIRED,
}


def normalize_institution(
    data: dict[str, Any],
    *,
    source_url: str,
    debug: bool = False,
) -> CivicStackResponse:
    is_waspada = data.pop("_waspada", False)

    result = {
        "institution_name": data.get("nama", data.get("name", data.get("nama_lembaga", ""))),
        "license_no": data.get("no_izin", data.get("nomor_izin", data.get("license_no", ""))),
        "institution_type": data.get("jenis", data.get("jenis_lembaga", data.get("type", ""))),
        "license_status": _parse_status(data.get("status", data.get("status_izin", "aktif"))).value,
        "regulated_products": _parse_products(data.get("produk", data.get("products", ""))),
        "domicile": data.get("kota", data.get("domisili", data.get("city", ""))),
        "website": data.get("website", data.get("url", "")),
        "on_waspada_list": is_waspada,
    }
    result = {
        k: v for k, v in result.items() if v not in (None, "", [], False) or k == "on_waspada_list"
    }

    # Waspada entries are flagged as SUSPENDED — the entity is unlicensed/problematic
    status = (
        RecordStatus.SUSPENDED
        if is_waspada
        else _parse_status(data.get("status", data.get("status_izin", "aktif")))
    )

    return CivicStackResponse(
        result=result,
        found=True,
        status=status,
        confidence=1.0 if data.get("no_izin") or data.get("nomor_izin") else 0.85,
        source_url=source_url,
        fetched_at=datetime.utcnow(),
        module=MODULE,
        raw=data if debug else None,
    )


def normalize_search_row(
    row: dict[str, Any],
    *,
    source_url: str,
    debug: bool = False,
) -> CivicStackResponse:
    result = {
        "institution_name": row.get("nama lembaga", row.get("nama", "")),
        "license_no": row.get("no. izin", row.get("nomor izin", "")),
        "institution_type": row.get("jenis lembaga", row.get("jenis", "")),
        "license_status": _parse_status(row.get("status", "aktif")).value,
        "domicile": row.get("kota", row.get("domisili", "")),
    }
    result = {k: v for k, v in result.items() if v}
    status = _parse_status(row.get("status", "aktif"))

    return CivicStackResponse(
        result=result,
        found=bool(result.get("institution_name")),
        status=status,
        confidence=0.8,
        source_url=source_url,
        fetched_at=datetime.utcnow(),
        module=MODULE,
        raw=row if debug else None,
    )


def _parse_status(status_str: str) -> RecordStatus:
    normalized = (status_str or "").strip().lower()
    for key, val in _STATUS_MAP.items():
        if key in normalized:
            return val
    return RecordStatus.ACTIVE if normalized else RecordStatus.NOT_FOUND


def _parse_products(products_raw: Any) -> list[str]:
    if isinstance(products_raw, list):
        return [str(p) for p in products_raw if p]
    if isinstance(products_raw, str) and products_raw:
        return [p.strip() for p in products_raw.split(",") if p.strip()]
    return []
