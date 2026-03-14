"""BPS normalizer — maps BPS API JSON to canonical fields."""

from __future__ import annotations

from typing import Any

_DATASET_MAP: dict[str, str] = {
    "subj_id": "subject_id",
    "subj": "subject_name",
    "kat_id": "category_id",
    "kat": "category_name",
    "n_notavail": "records_unavailable",
}

_INDICATOR_MAP: dict[str, str] = {
    "table_id": "table_id",
    "title": "title",
    "note": "note",
    "updt_date": "last_updated",
    "size": "record_count",
}

_REGION_MAP: dict[str, str] = {
    "kode_wilayah": "region_code",
    "nama_wilayah": "region_name",
    "id_wilayah": "region_code",
    "nama": "region_name",
    "level": "level",
}


def _confidence(rec: dict[str, Any], query: str) -> float:
    if not query:
        return 0.8
    name = (rec.get("subject_name") or "").lower()
    q = query.lower()
    if q in name:
        return 1.0 if q == name else 0.9
    words = set(q.split())
    name_words = set(name.split())
    overlap = len(words & name_words) / max(len(words), 1)
    return round(max(0.5, overlap), 2)


def normalize_dataset(raw: dict[str, Any], *, query: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for src, dst in _DATASET_MAP.items():
        val = raw.get(src)
        if val is not None and val != "":
            out[dst] = val

    out["_confidence"] = _confidence(out, query)
    return out


def normalize_indicator(
    raw: dict[str, Any],
    *,
    indicator_id: str,
    region_code: str,
) -> dict[str, Any]:
    out: dict[str, Any] = {"indicator_id": indicator_id, "region_code": region_code}
    for src, dst in _INDICATOR_MAP.items():
        val = raw.get(src)
        if val is not None and val != "":
            out[dst] = val

    # Extract time series from datacontent if present
    datacontent = raw.get("datacontent") or {}
    if datacontent:
        series: list[dict[str, Any]] = []
        for period, value in datacontent.items():
            try:
                series.append(
                    {"period": period, "value": float(value) if value not in ("", "-") else None}
                )
            except (ValueError, TypeError):
                series.append({"period": period, "value": None})
        out["time_series"] = sorted(series, key=lambda x: x["period"])

    return out


def normalize_region(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for src, dst in _REGION_MAP.items():
        val = raw.get(src)
        if val is not None and val != "" and dst not in out:
            out[dst] = val
    return out
