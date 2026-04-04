"""DJPB normalizer — maps API JSON to canonical fields."""

from __future__ import annotations

from typing import Any

_THEME_MAP: dict[str, str] = {
    "id_tematik": "theme_id",
    "nama_tema": "theme_name",
    "nama_tema_en": "theme_name_en",
    "tahun": "year",
    "target": "target_amount",
    "realisasi": "realization_amount",
    "capaian": "achievement_pct",
}

_ACCOUNT_MAP: dict[str, str] = {
    "code": "code",
    "title": "name",
    "title_en": "name_en",
}


def normalize_budget_theme(raw: dict[str, Any]) -> dict[str, Any]:
    """Map API budget theme data to canonical schema."""
    out: dict[str, Any] = {}

    # Map top-level fields
    for src, dst in _THEME_MAP.items():
        val = raw.get(src)
        if val is not None and val != "":
            out[dst] = val

    # Process accounts list
    list_akun = raw.get("list_akun", [])
    if list_akun:
        accounts: list[dict[str, Any]] = []
        for akun_item in list_akun:
            akun_data = akun_item.get("akun", {})
            account: dict[str, Any] = {}

            # Map account fields
            for src, dst in _ACCOUNT_MAP.items():
                val = akun_data.get(src)
                if val is not None and val != "":
                    account[dst] = val

            # Add allocation and realization from parent level
            if "alokasi" in akun_item:
                account["allocation"] = akun_item["alokasi"]
            if "realisasi" in akun_item:
                account["realization"] = akun_item["realisasi"]

            accounts.append(account)

        out["accounts"] = accounts

    return out
