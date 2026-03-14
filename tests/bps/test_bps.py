"""Tests for the BPS module — VCR cassettes + normalizer unit tests."""

from __future__ import annotations

import os

import pytest
import vcr

from civic_stack.bps.normalizer import normalize_dataset, normalize_indicator, normalize_region
from civic_stack.bps.scraper import get_indicator, search
from civic_stack.shared.schema import CivicStackResponse

# Patch the API key for tests so _api_key() doesn't raise
os.environ.setdefault("BPS_API_KEY", "TEST_KEY")

CASSETTE_DIR = "tests/bps/cassettes"
vcr_config = vcr.VCR(
    cassette_library_dir=CASSETTE_DIR,
    record_mode="none",
    match_on=["uri", "method"],
    decode_compressed_response=True,
)


# ---------------------------------------------------------------------------
# Normalizer unit tests
# ---------------------------------------------------------------------------


def test_normalize_dataset_full():
    raw = {
        "subj_id": "23",
        "subj": "Kemiskinan dan Ketimpangan",
        "kat_id": "2",
        "kat": "Sosial",
        "n_notavail": 0,
    }
    result = normalize_dataset(raw, query="kemiskinan")
    assert result["subject_id"] == "23"
    assert result["subject_name"] == "Kemiskinan dan Ketimpangan"
    assert result["category_name"] == "Sosial"
    assert result["_confidence"] >= 0.9


def test_normalize_indicator_with_timeseries():
    raw = {
        "table_id": "528",
        "title": "Persentase Penduduk Miskin",
        "updt_date": "2024-01-15",
        "datacontent": {"2019": "9.22", "2020": "10.19", "2021": "9.71"},
    }
    result = normalize_indicator(raw, indicator_id="528", region_code="0000")
    assert result["indicator_id"] == "528"
    assert result["title"] == "Persentase Penduduk Miskin"
    assert len(result["time_series"]) == 3
    assert result["time_series"][0]["period"] == "2019"
    assert result["time_series"][0]["value"] == 9.22


def test_normalize_region():
    raw = {"id_wilayah": "31", "nama": "DKI JAKARTA", "level": "1"}
    result = normalize_region(raw)
    assert result["region_code"] == "31"
    assert result["region_name"] == "DKI JAKARTA"


# ---------------------------------------------------------------------------
# Scraper tests — VCR replays
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_datasets():
    with vcr_config.use_cassette("dataset_search.yaml"):
        results = await search("kemiskinan")
    assert len(results) == 3
    assert all(r.module == "bps" for r in results)
    assert results[0].result["subject_name"] == "Kemiskinan dan Ketimpangan"


@pytest.mark.asyncio
async def test_search_not_found():
    with vcr_config.use_cassette("dataset_not_found.yaml"):
        results = await search("dataset tidak ada xyz123")
    assert results == []


@pytest.mark.asyncio
async def test_get_indicator_timeseries():
    with vcr_config.use_cassette("indicator_timeseries.yaml"):
        resp = await get_indicator("528", region_code="0000")
    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.module == "bps"
    assert resp.result["title"] == "Persentase Penduduk Miskin (Persen)"
    series = resp.result["time_series"]
    assert len(series) == 5
    assert series[-1]["period"] == "2023"
    assert series[-1]["value"] == 9.03


@pytest.mark.asyncio
async def test_response_json_serializable():
    with vcr_config.use_cassette("indicator_timeseries.yaml"):
        resp = await get_indicator("528")
    data = resp.model_dump(mode="json")
    assert data["module"] == "bps"
    assert isinstance(data["fetched_at"], str)
