"""Tests for the BMKG module — VCR cassettes + normalizer unit tests."""

from __future__ import annotations

import pytest
import vcr

from modules.bmkg.normalizer import normalize_earthquake, normalize_forecast
from modules.bmkg.scraper import get_earthquake_history, get_latest_earthquake
from shared.schema import CivicStackResponse, RecordStatus

CASSETTE_DIR = "tests/bmkg/cassettes"
vcr_config = vcr.VCR(
    cassette_library_dir=CASSETTE_DIR,
    record_mode="none",
    match_on=["uri", "method"],
    decode_content_encoding=True,
)


# ---------------------------------------------------------------------------
# Normalizer unit tests
# ---------------------------------------------------------------------------

def test_normalize_earthquake_full():
    raw = {
        "Tanggal":     "13 Mar 2026",
        "Jam":         "06:15:42 WIB",
        "DateTime":    "2026-03-12T23:15:42+00:00",
        "Lintang":     "2.45 LS",
        "Bujur":       "128.73 BT",
        "Magnitude":   "5.2",
        "Kedalaman":   "10 km",
        "Wilayah":     "Pusat gempa berada di darat 23 km Barat Laut Ternate",
        "Potensi":     "Gempa ini dirasakan untuk diwaspadai",
        "Dirasakan":   "III Ternate",
    }
    result = normalize_earthquake(raw)
    assert result["magnitude"] == 5.2
    assert result["depth_km"] == 10.0
    assert result["region"] == "Pusat gempa berada di darat 23 km Barat Laut Ternate"
    assert result["tsunami_warning"] is False


def test_normalize_earthquake_tsunami_warning():
    raw = {
        "Magnitude":  "7.5",
        "Kedalaman":  "18 km",
        "Wilayah":    "Selatan Jawa",
        "Potensi":    "BERPOTENSI TSUNAMI",
    }
    result = normalize_earthquake(raw)
    assert result["tsunami_warning"] is True


def test_normalize_earthquake_no_tsunami_not():
    raw = {
        "Magnitude": "4.8",
        "Potensi":   "Tidak berpotensi tsunami",
    }
    result = normalize_earthquake(raw)
    assert result["tsunami_warning"] is False


def test_normalize_forecast_xml():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <data>
      <forecast>
        <area id="501331" latitude="-6.21" longitude="106.85"
              description="Jakarta Pusat" domain="DKIJakarta">
          <parameter id="t" description="Temperature" unit="C">
            <timerange day="0" hour="0600" type="hourly">
              <value unit="C">28</value>
            </timerange>
            <timerange day="1" hour="0600" type="hourly">
              <value unit="C">30</value>
            </timerange>
          </parameter>
        </area>
      </forecast>
    </data>"""
    result = normalize_forecast(xml, city="jakarta", province="DKIJakarta")
    assert result is not None
    assert result["city"] == "jakarta"
    assert result["province"] == "DKIJakarta"
    assert len(result["forecast"]) >= 2


# ---------------------------------------------------------------------------
# Scraper tests — VCR replays
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_latest_earthquake():
    with vcr_config.use_cassette("earthquake_latest.yaml"):
        resp = await get_latest_earthquake()
    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.status == RecordStatus.ACTIVE
    assert resp.module == "bmkg"
    assert resp.result["magnitude"] == 5.2
    assert resp.result["depth_km"] == 10.0
    assert "Ternate" in resp.result["region"]
    assert resp.result["tsunami_warning"] is False


@pytest.mark.asyncio
async def test_get_earthquake_history():
    with vcr_config.use_cassette("earthquake_history.yaml"):
        results = await get_earthquake_history()
    assert len(results) == 3
    assert all(r.module == "bmkg" for r in results)
    magnitudes = [r.result["magnitude"] for r in results]
    assert 6.1 in magnitudes


@pytest.mark.asyncio
async def test_earthquake_history_region_filter():
    with vcr_config.use_cassette("earthquake_history.yaml"):
        results = await get_earthquake_history("Bali")
    assert len(results) == 1
    assert "Bali" in results[0].result["region"]


@pytest.mark.asyncio
async def test_response_json_serializable():
    with vcr_config.use_cassette("earthquake_latest.yaml"):
        resp = await get_latest_earthquake()
    data = resp.model_dump(mode="json")
    assert data["module"] == "bmkg"
    assert isinstance(data["fetched_at"], str)
