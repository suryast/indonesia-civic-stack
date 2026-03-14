"""
Tests for the BPOM module — all run against VCR cassettes (no live portal calls).
"""

from __future__ import annotations

import pytest
import vcr

from civic_stack.bpom.scraper import fetch, search
from civic_stack.shared.schema import CivicStackResponse, RecordStatus

CASSETTE_DIR = "tests/bpom/cassettes"

vcr_config = vcr.VCR(
    cassette_library_dir=CASSETTE_DIR,
    record_mode="none",  # CI: never record new cassettes
    match_on=["uri", "method"],
)


@pytest.mark.asyncio
async def test_fetch_found():
    with vcr_config.use_cassette("found.yaml"):
        resp = await fetch("BPOM MD 123456789012")

    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.status == RecordStatus.ACTIVE
    assert resp.module == "bpom"
    assert resp.confidence == 1.0
    assert resp.result is not None
    assert resp.result["product_name"] == "MIE GORENG SPESIAL RASA AYAM"
    assert resp.result["company"] == "PT INDOFOOD SUKSES MAKMUR TBK"
    assert resp.result["registration_no"] == "BPOM MD 123456789012"
    assert resp.raw is None  # debug=False by default


@pytest.mark.asyncio
async def test_fetch_found_debug_includes_raw():
    with vcr_config.use_cassette("found.yaml"):
        resp = await fetch("BPOM MD 123456789012", debug=True)

    assert resp.raw is not None
    assert isinstance(resp.raw, dict)


@pytest.mark.asyncio
async def test_fetch_not_found():
    with vcr_config.use_cassette("not_found.yaml"):
        resp = await fetch("BPOM MD 000000000000")

    assert isinstance(resp, CivicStackResponse)
    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND
    assert resp.result is None


@pytest.mark.asyncio
async def test_fetch_expired():
    with vcr_config.use_cassette("expired.yaml"):
        resp = await fetch("BPOM MD 999900000001")

    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.status == RecordStatus.EXPIRED
    assert resp.result["registration_status"] == RecordStatus.EXPIRED.value


@pytest.mark.asyncio
async def test_search_returns_multiple():
    with vcr_config.use_cassette("search_multi.yaml"):
        results = await search("paracetamol")

    assert isinstance(results, list)
    assert len(results) == 3
    for r in results:
        assert isinstance(r, CivicStackResponse)
        assert r.found is True
        assert r.module == "bpom"
        # Search results have lower confidence
        assert r.confidence == 0.8


@pytest.mark.asyncio
async def test_search_result_fields():
    with vcr_config.use_cassette("search_multi.yaml"):
        results = await search("paracetamol")

    first = results[0]
    assert first.result is not None
    assert "registration_no" in first.result
    assert "product_name" in first.result
    assert "company" in first.result


@pytest.mark.asyncio
async def test_response_json_serializable():
    """CivicStackResponse must be JSON-serialisable for MCP tool returns."""
    with vcr_config.use_cassette("found.yaml"):
        resp = await fetch("BPOM MD 123456789012")

    data = resp.model_dump(mode="json")
    assert isinstance(data["fetched_at"], str)
    assert data["module"] == "bpom"
    assert data["status"] in [s.value for s in RecordStatus]
