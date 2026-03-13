"""BMKG normalizer — maps BMKG API JSON/XML responses to canonical fields."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any


_EARTHQUAKE_MAP: dict[str, str] = {
    "Tanggal":     "date",
    "Jam":         "time",
    "DateTime":    "datetime_utc",
    "Coordinates": "coordinates",
    "Lintang":     "latitude",
    "Bujur":       "longitude",
    "Magnitude":   "magnitude",
    "Kedalaman":   "depth_km",
    "Wilayah":     "region",
    "Potensi":     "tsunami_potential",
    "Dirasakan":   "felt_reports",
    "Shakemap":    "shakemap_url",
}

_ALERT_MAP: dict[str, str] = {
    "id":          "alert_id",
    "tipe":        "alert_type",
    "wilayah":     "region",
    "keterangan":  "description",
    "tanggal":     "date",
    "jam":         "time",
    "level":       "severity_level",
}


def normalize_earthquake(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for src, dst in _EARTHQUAKE_MAP.items():
        val = raw.get(src)
        if val is not None and val != "":
            out[dst] = val

    # Parse magnitude to float
    if "magnitude" in out:
        try:
            out["magnitude"] = float(str(out["magnitude"]).replace(",", "."))
        except ValueError:
            pass

    # Parse depth to float
    if "depth_km" in out:
        depth_str = re.sub(r"[^\d.]", "", str(out["depth_km"]))
        try:
            out["depth_km"] = float(depth_str)
        except ValueError:
            pass

    # Determine tsunami flag from potential text
    potential = str(out.get("tsunami_potential", "")).upper()
    out["tsunami_warning"] = "TSUNAMI" in potential and "TIDAK" not in potential

    return out


def normalize_alert(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for src, dst in _ALERT_MAP.items():
        val = raw.get(src)
        if val is not None and val != "":
            out[dst] = val
    return out


def normalize_forecast(xml_text: str, *, city: str, province: str) -> dict[str, Any] | None:
    """Parse BMKG DigitalForecast XML into a minimal structured dict."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None

    ns = {"bmkg": ""}  # BMKG XML may not use namespace

    # Find area elements — look for city name match
    areas = root.findall(".//area") or root.findall(".//{*}area")
    target_area = None
    city_lower = city.lower()
    for area in areas:
        area_desc = (area.get("description") or "").lower()
        if city_lower in area_desc or area_desc in city_lower:
            target_area = area
            break
    if target_area is None and areas:
        target_area = areas[0]  # fallback: first area

    if target_area is None:
        return None

    area_name = target_area.get("description", province)
    forecasts: list[dict[str, Any]] = []

    for param in target_area.findall(".//parameter") or []:
        param_id = param.get("id", "")
        param_desc = param.get("description", "")
        for timerange in param.findall(".//timerange") or []:
            day  = timerange.get("day", "")
            hour = timerange.get("hour", "")
            value_el = timerange.find("value")
            if value_el is not None:
                forecasts.append({
                    "parameter":   param_id,
                    "description": param_desc,
                    "day":         day,
                    "hour":        hour,
                    "value":       (value_el.text or "").strip(),
                    "unit":        value_el.get("unit", ""),
                })

    return {
        "city":     city,
        "province": province,
        "area":     area_name,
        "forecast": forecasts[:50],  # cap at 50 entries
    }
