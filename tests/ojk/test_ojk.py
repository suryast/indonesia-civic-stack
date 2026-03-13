"""Tests for the OJK module — VCR cassettes."""

from __future__ import annotations

import pytest
import vcr

from modules.ojk.scraper import check_waspada, fetch
from shared.schema import CivicStackResponse, RecordStatus

CASSETTE_DIR = "tests/ojk/cassettes"
vcr_config = vcr.VCR(cassette_library_dir=CASSETTE_DIR, record_mode="none",
                     match_on=["uri", "method"], decode_content_encoding=True)


@pytest.mark.asyncio
async def test_fetch_institution_found():
    with vcr_config.use_cassette("institution_found.yaml"):
        resp = await fetch("Akulaku")
    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.status == RecordStatus.ACTIVE
    assert resp.module == "ojk"
    assert resp.result["institution_name"] == "PT AKULAKU FINANCE INDONESIA"
    assert resp.result["license_no"] == "KEP-249/NB.11/2018"
    assert isinstance(resp.result["regulated_products"], list)


@pytest.mark.asyncio
async def test_fetch_institution_not_found():
    with vcr_config.use_cassette("institution_not_found.yaml"):
        resp = await fetch("LEMBAGA TIDAK ADA")
    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_waspada_found():
    with vcr_config.use_cassette("waspada_found.yaml"):
        resp = await check_waspada("Untung Berlipat")
    assert resp.found is True
    assert resp.status == RecordStatus.SUSPENDED
    assert resp.result["on_waspada_list"] is True
    assert resp.result["institution_name"] == "PT UNTUNG BERLIPAT INVESTASI"


@pytest.mark.asyncio
async def test_response_json_serializable():
    with vcr_config.use_cassette("institution_found.yaml"):
        resp = await fetch("Akulaku")
    data = resp.model_dump(mode="json")
    assert data["module"] == "ojk"
    assert isinstance(data["fetched_at"], str)
