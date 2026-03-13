"""Tests for the KPU module — VCR cassettes, no live API calls."""

from __future__ import annotations

import pytest
import vcr

from modules.kpu.scraper import fetch, get_election_results, search
from shared.schema import CivicStackResponse, RecordStatus

CASSETTE_DIR = "tests/kpu/cassettes"
vcr_config = vcr.VCR(
    cassette_library_dir=CASSETTE_DIR,
    record_mode="none",
    match_on=["uri", "method"],
    decode_compressed_response=True,
)


@pytest.mark.asyncio
async def test_fetch_candidate_found():
    with vcr_config.use_cassette("candidate_found.yaml"):
        resp = await fetch("Budi Santoso")
    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.status == RecordStatus.ACTIVE
    assert resp.module == "kpu"
    assert resp.result["name"] == "BUDI SANTOSO"
    assert resp.result["party"] == "PDIP"
    assert resp.result["elected"] is True
    assert resp.result["vote_count"] == 45230


@pytest.mark.asyncio
async def test_fetch_candidate_not_found():
    with vcr_config.use_cassette("candidate_not_found.yaml"):
        resp = await fetch("KANDIDAT TIDAK ADA")
    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_search_returns_multiple():
    with vcr_config.use_cassette("search_multi.yaml"):
        results = await search("Ahmad")
    assert len(results) == 2
    assert all(r.module == "kpu" for r in results)
    assert results[0].result["name"] == "AHMAD YUSUF"
    assert results[1].result["election_type"] == "dprd_prov"


@pytest.mark.asyncio
async def test_election_results():
    with vcr_config.use_cassette("election_results.yaml"):
        resp = await get_election_results("31", "dpr")
    assert resp.found is True
    assert resp.result["region_code"] == "31"
    assert "results_by_party" in resp.result
    assert resp.result["results_by_party"]["PDIP"] == 1234567
    assert resp.result["tps_reported"] == 12450


@pytest.mark.asyncio
async def test_response_json_serializable():
    with vcr_config.use_cassette("candidate_found.yaml"):
        resp = await fetch("Budi Santoso")
    data = resp.model_dump(mode="json")
    assert data["module"] == "kpu"
    assert isinstance(data["fetched_at"], str)
