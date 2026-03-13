"""LPSE normalizer — maps SPSE API JSON responses to flat dicts."""

from __future__ import annotations

import re
from typing import Any


# SPSE vendor JSON keys → our canonical keys
_VENDOR_KEY_MAP: dict[str, str] = {
    "kodeRekanan":   "vendor_id",
    "namaRekanan":   "vendor_name",
    "npwp":          "npwp",
    "alamat":        "address",
    "kota":          "city",
    "provinsi":      "province",
    "telepon":       "phone",
    "email":         "email",
    "statusAktif":   "is_active",
    "jenisUsaha":    "business_type",
    "kualifikasi":   "qualification",
    "bidangUsaha":   "business_field",
}

# SPSE tender JSON keys → canonical keys
_TENDER_KEY_MAP: dict[str, str] = {
    "kode":               "tender_id",
    "namaPaket":          "tender_name",
    "namaSatker":         "procuring_entity",
    "kodeSatker":         "entity_code",
    "tahapTender":        "tender_stage",
    "metodePengadaan":    "procurement_method",
    "nilaiPagu":          "ceiling_value",
    "nilaiHPS":           "hps_value",
    "tanggalPembuatan":   "created_date",
    "tanggalTutup":       "closing_date",
    "statusTender":       "tender_status",
    "sumberDana":         "funding_source",
    "linkLelang":         "tender_url",
}

_NPWP_RE = re.compile(r"\d{2}\.\d{3}\.\d{3}\.\d{1}-\d{3}\.\d{3}")


def _clean_npwp(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip().replace(" ", "")
    m = _NPWP_RE.search(raw)
    return m.group() if m else raw or None


def normalize_vendor(raw: dict[str, Any]) -> dict[str, Any] | None:
    if not raw:
        return None
    out: dict[str, Any] = {}
    for src, dst in _VENDOR_KEY_MAP.items():
        val = raw.get(src)
        if val is not None and val != "":
            out[dst] = val

    # normalise NPWP format
    if "npwp" in out:
        out["npwp"] = _clean_npwp(str(out["npwp"]))

    # coerce boolean
    if "is_active" in out:
        out["is_active"] = bool(out["is_active"])

    # ensure name present
    if not out.get("vendor_name"):
        return None

    return out


def normalize_tender(raw: dict[str, Any]) -> dict[str, Any] | None:
    if not raw:
        return None
    out: dict[str, Any] = {}
    for src, dst in _TENDER_KEY_MAP.items():
        val = raw.get(src)
        if val is not None and val != "":
            out[dst] = val

    # coerce numeric fields
    for field in ("ceiling_value", "hps_value"):
        if field in out:
            try:
                out[field] = float(str(out[field]).replace(",", "").replace(".", ""))
            except (ValueError, TypeError):
                pass

    if not out.get("tender_name"):
        return None

    return out
