"""SIMBG normalizer — maps SIMBG API JSON to canonical permit fields."""

from __future__ import annotations

from typing import Any

# SIMBG API key → canonical key
_PERMIT_MAP: dict[str, str] = {
    "nomor_pbg": "permit_number",
    "nomor_imb": "permit_number",  # legacy IMB field
    "no_imb": "permit_number",
    "jenis_izin": "permit_type",
    "nama_pemilik": "owner_name",
    "alamat_bangunan": "address",
    "alamat": "address",
    "kelurahan": "kelurahan",
    "kecamatan": "kecamatan",
    "kota": "city",
    "kabupaten_kota": "city",
    "provinsi": "province",
    "luas_bangunan": "floor_area_m2",
    "jumlah_lantai": "floor_count",
    "fungsi_bangunan": "building_function",
    "status_pbg": "permit_status",
    "status_imb": "permit_status",
    "tanggal_terbit": "issue_date",
    "tanggal_berlaku": "valid_until",
    "instansi_penerbit": "issuing_authority",
    "koordinat": "coordinates",
    "latitude": "latitude",
    "longitude": "longitude",
}

_SEARCH_MAP: dict[str, str] = {
    "nomor_pbg": "permit_number",
    "nomor_imb": "permit_number",
    "no_imb": "permit_number",
    "nama_pemilik": "owner_name",
    "alamat_bangunan": "address",
    "alamat": "address",
    "kota": "city",
    "kabupaten_kota": "city",
    "jenis_izin": "permit_type",
    "status_pbg": "permit_status",
    "status_imb": "permit_status",
    "fungsi_bangunan": "building_function",
}


def normalize_permit(raw: dict[str, Any]) -> dict[str, Any] | None:
    if not raw:
        return None
    out: dict[str, Any] = {}
    for src, dst in _PERMIT_MAP.items():
        val = raw.get(src)
        if val is not None and val != "" and dst not in out:
            out[dst] = val

    # Coerce numeric fields
    import contextlib

    for field in ("floor_area_m2", "floor_count"):
        if field in out:
            with contextlib.suppress(ValueError, TypeError):
                out[field] = float(str(out[field]).replace(",", "."))

    # Must have at least address or permit_number
    if not out.get("permit_number") and not out.get("address"):
        return None

    return out


def normalize_search_result(raw: dict[str, Any]) -> dict[str, Any] | None:
    if not raw:
        return None
    out: dict[str, Any] = {}
    for src, dst in _SEARCH_MAP.items():
        val = raw.get(src)
        if val is not None and val != "" and dst not in out:
            out[dst] = val
    if not out.get("permit_number") and not out.get("address"):
        return None
    return out
