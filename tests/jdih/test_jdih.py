"""
Tests for the JDIH module — monkeypatched Playwright scrape layer.

The scraper drives peraturan.go.id with Playwright (JS-rendered, no API);
tests stub _scrape_regulation_list()/_scrape_regulation_detail() and
exercise the public fetch()/search()/list_recent() semantics on top.
"""

from __future__ import annotations

import pytest

from civic_stack.jdih.scraper import fetch, list_recent, search
from civic_stack.shared.schema import CivicStackResponse, RecordStatus

REGULATIONS = [
    {
        "regulation_id": "uu-no-1-tahun-2023",
        "regulation_type": "uu",
        "number": "1",
        "year": "2023",
        "title": "UU No. 1 Tahun 2023 tentang Kitab Undang-Undang Hukum Pidana",
        "status": "ACTIVE",
        "about": None,
        "full_url": "https://peraturan.go.id/id/uu-no-1-tahun-2023",
    },
    {
        "regulation_id": "uu-no-27-tahun-2022",
        "regulation_type": "uu",
        "number": "27",
        "year": "2022",
        "title": "UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi",
        "status": "ACTIVE",
        "about": None,
        "full_url": "https://peraturan.go.id/id/uu-no-27-tahun-2022",
    },
]

DETAIL = {
    "regulation_id": "uu-no-1-tahun-2023",
    "regulation_type": "uu",
    "number": "1",
    "year": "2023",
    "title": "Kitab Undang-Undang Hukum Pidana",
    "status": "ACTIVE",
    "about": "Pembaruan hukum pidana nasional",
    "full_url": "https://peraturan.go.id/id/uu-no-1-tahun-2023",
}


@pytest.fixture
def mock_scrape(monkeypatch):
    async def _mock_list(regulation_type="uu", *, limit=20, proxy_url=None):
        return REGULATIONS[:limit]

    async def _mock_detail(regulation_id, *, proxy_url=None):
        if regulation_id == DETAIL["regulation_id"]:
            return DETAIL
        return None

    monkeypatch.setattr("civic_stack.jdih.scraper._scrape_regulation_list", _mock_list)
    monkeypatch.setattr("civic_stack.jdih.scraper._scrape_regulation_detail", _mock_detail)


@pytest.mark.asyncio
async def test_search_found(mock_scrape):
    """search() filters the scraped listing by keyword in title."""
    results = await search("hukum pidana")

    assert isinstance(results, list)
    assert len(results) == 1
    assert all(isinstance(r, CivicStackResponse) for r in results)

    first = results[0]
    assert first.found is True
    assert first.module == "jdih"
    assert first.status == RecordStatus.ACTIVE
    assert first.result is not None
    assert first.result["regulation_id"] == "uu-no-1-tahun-2023"
    assert first.confidence == 1.0


@pytest.mark.asyncio
async def test_search_not_found(mock_scrape):
    """search() returns an empty list when no titles match."""
    results = await search("nonexistent keyword")

    assert isinstance(results, list)
    assert results == []


@pytest.mark.asyncio
async def test_fetch_found(mock_scrape):
    """fetch() returns the regulation detail by ID."""
    resp = await fetch("uu-no-1-tahun-2023")

    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.module == "jdih"
    assert resp.status == RecordStatus.ACTIVE
    assert resp.result is not None
    assert resp.result["about"] == "Pembaruan hukum pidana nasional"
    assert resp.source_url == DETAIL["full_url"]


@pytest.mark.asyncio
async def test_fetch_not_found(mock_scrape):
    """fetch() returns a NOT_FOUND envelope for an unknown regulation ID."""
    resp = await fetch("uu-no-999-tahun-1999")

    assert isinstance(resp, CivicStackResponse)
    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_list_recent(mock_scrape):
    """list_recent() wraps every scraped regulation in an envelope."""
    results = await list_recent("uu", limit=20)

    assert len(results) == 2
    assert all(r.found for r in results)
    assert results[1].result["regulation_id"] == "uu-no-27-tahun-2022"


@pytest.mark.asyncio
async def test_response_json_serializable(mock_scrape):
    """CivicStackResponse must be JSON-serialisable for MCP tool returns."""
    resp = await fetch("uu-no-1-tahun-2023")

    data = resp.model_dump(mode="json")
    assert isinstance(data["fetched_at"], str)
    assert data["module"] == "jdih"
    assert data["status"] in [s.value for s in RecordStatus]
