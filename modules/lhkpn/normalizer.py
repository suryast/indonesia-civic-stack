"""LHKPN normalizer — maps KPK API JSON to canonical fields."""

from __future__ import annotations

import re
from typing import Any


# API field → canonical field
_OFFICIAL_MAP: dict[str, str] = {
    "nama":              "official_name",
    "nama_penyelenggara":"official_name",
    "jabatan":           "position",
    "instansi":          "ministry",
    "satuan_kerja":      "work_unit",
    "tahun_laporan":     "declaration_year",
    "tgl_selesai":       "submission_date",
    "periode":           "declaration_period",
    "jenis_laporan":     "report_type",
    "no_laporan":        "report_number",
    "id_laporan":        "report_id",
    # asset summary fields
    "total_harta":               "total_assets_idr",
    "jumlah_harta":              "total_assets_idr",
    "total_hutang":              "total_liabilities_idr",
    "jumlah_hutang":             "total_liabilities_idr",
    "harta_bersih":              "net_assets_idr",
    "jumlah_harta_bersih":       "net_assets_idr",
    # asset breakdown
    "harta_tidak_bergerak":      "immovable_property_idr",
    "harta_bergerak":            "movable_property_idr",
    "surat_berharga":            "securities_idr",
    "kas_setara_kas":            "cash_idr",
    "harta_lainnya":             "other_assets_idr",
    # income
    "penghasilan_dari_jabatan":  "income_from_position_idr",
    "penghasilan_lainnya":       "other_income_idr",
}

_IDR_RE = re.compile(r"[Rp\s,.]")


def _parse_idr(val: Any) -> int | None:
    """Parse IDR value from various formats: 'Rp 1.234.567', 1234567, '1,234,567'."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    cleaned = _IDR_RE.sub("", str(val))
    try:
        return int(cleaned)
    except ValueError:
        return None


def _confidence(rec: dict[str, Any], query: str) -> float:
    name = (rec.get("official_name") or "").upper()
    q = query.upper()
    if not q:
        return 0.8
    if q == name:
        return 1.0
    if q in name or name in q:
        return 0.9
    # check word overlap
    q_words = set(q.split())
    n_words = set(name.split())
    overlap = len(q_words & n_words) / max(len(q_words), 1)
    return round(max(0.5, overlap), 2)


def normalize_declaration(raw: dict[str, Any], *, query: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for src, dst in _OFFICIAL_MAP.items():
        val = raw.get(src)
        if val is not None and val != "":
            if dst not in out:  # first match wins (handles alias keys)
                out[dst] = val

    # Parse all IDR fields
    _idr_fields = [
        "total_assets_idr", "total_liabilities_idr", "net_assets_idr",
        "immovable_property_idr", "movable_property_idr", "securities_idr",
        "cash_idr", "other_assets_idr",
        "income_from_position_idr", "other_income_idr",
    ]
    for field in _idr_fields:
        if field in out:
            out[field] = _parse_idr(out[field])

    # Compute net assets if missing but total and liabilities are present
    if out.get("net_assets_idr") is None:
        total = out.get("total_assets_idr")
        liab  = out.get("total_liabilities_idr")
        if isinstance(total, int) and isinstance(liab, int):
            out["net_assets_idr"] = total - liab

    # Build asset_breakdown sub-dict for convenience
    breakdown_keys = [
        "immovable_property_idr", "movable_property_idr", "securities_idr",
        "cash_idr", "other_assets_idr",
    ]
    breakdown = {k: out.pop(k) for k in breakdown_keys if k in out}
    if breakdown:
        out["asset_breakdown"] = breakdown

    out["_confidence"] = _confidence(out, query)
    return out


def normalize_search_result(raw: dict[str, Any]) -> dict[str, Any]:
    """Lightweight normalization for search result list items."""
    out: dict[str, Any] = {}
    for src, dst in _OFFICIAL_MAP.items():
        val = raw.get(src)
        if val is not None and val != "" and dst not in out:
            out[dst] = val
    return out
