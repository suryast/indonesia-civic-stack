"""
Tests for the DJPB module — monkeypatched data-series API (no live calls).

The scraper talks to data-apbn.kemenkeu.go.id's JSON API via
_fetch_data_series(); tests stub that boundary and exercise the public
fetch()/search()/get_budget_summary() semantics on top of it.
"""

from __future__ import annotations

import pytest

from civic_stack.djpb.scraper import fetch, get_budget_summary, search
from civic_stack.shared.schema import CivicStackResponse, RecordStatus

THEMES = [
    {
        "id_tematik": "pendidikan",
        "nama_tema": "Anggaran Pendidikan",
        "nama_tema_en": "Education Budget",
        "tahun": "2026 - 2026",
        "target": 660_000_000_000_000,
        "realisasi": 154_000_000_000_000,
        "capaian": 23.3,
        "list_akun": [
            {
                "akun": {"code": "01", "title": "Belanja Pegawai", "title_en": "Personnel"},
                "alokasi": 100_000_000_000_000,
                "realisasi": 25_000_000_000_000,
            }
        ],
    },
    {
        "id_tematik": "kesehatan",
        "nama_tema": "Anggaran Kesehatan",
        "nama_tema_en": "Health Budget",
        "tahun": "2025 - 2025",
        "target": 187_000_000_000_000,
        "realisasi": 60_000_000_000_000,
        "capaian": 32.1,
    },
]


@pytest.fixture
def mock_data_series(monkeypatch):
    async def _mock(*, proxy_url=None):
        return THEMES

    monkeypatch.setattr("civic_stack.djpb.scraper._fetch_data_series", _mock)


@pytest.fixture
def mock_empty_data_series(monkeypatch):
    async def _mock(*, proxy_url=None):
        return []

    monkeypatch.setattr("civic_stack.djpb.scraper._fetch_data_series", _mock)


@pytest.mark.asyncio
async def test_search_found(mock_data_series):
    """search() matches keyword against theme names (id + en)."""
    results = await search("anggaran")

    assert isinstance(results, list)
    assert len(results) == 2
    assert all(isinstance(r, CivicStackResponse) for r in results)

    first = results[0]
    assert first.found is True
    assert first.module == "djpb"
    assert first.status == RecordStatus.ACTIVE
    assert first.result is not None
    assert first.result["theme_id"] == "pendidikan"
    assert first.result["theme_name"] == "Anggaran Pendidikan"


@pytest.mark.asyncio
async def test_search_english_name(mock_data_series):
    """search() also matches the English theme name."""
    results = await search("health")

    assert len(results) == 1
    assert results[0].result["theme_id"] == "kesehatan"


@pytest.mark.asyncio
async def test_search_not_found(mock_data_series):
    """search() returns an empty list when nothing matches."""
    results = await search("nonexistent")

    assert isinstance(results, list)
    assert results == []


@pytest.mark.asyncio
async def test_fetch_found(mock_data_series):
    """fetch() returns the theme matching id_tematik, with accounts."""
    resp = await fetch("pendidikan")

    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.module == "djpb"
    assert resp.status == RecordStatus.ACTIVE
    assert resp.result is not None
    assert resp.result["year"] == "2026 - 2026"
    assert resp.result["accounts"][0]["name"] == "Belanja Pegawai"


@pytest.mark.asyncio
async def test_fetch_not_found(mock_data_series):
    """fetch() returns a NOT_FOUND envelope for an unknown theme id."""
    resp = await fetch("does-not-exist")

    assert isinstance(resp, CivicStackResponse)
    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_fetch_api_unavailable(mock_empty_data_series):
    """fetch() degrades to NOT_FOUND when the API returns nothing."""
    resp = await fetch("pendidikan")

    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_budget_summary_year_filter(mock_data_series):
    """get_budget_summary() filters themes by year substring."""
    all_themes = await get_budget_summary()
    only_2026 = await get_budget_summary(year="2026")

    assert len(all_themes) == 2
    assert len(only_2026) == 1
    assert only_2026[0].result["theme_id"] == "pendidikan"


@pytest.mark.asyncio
async def test_response_json_serializable(mock_data_series):
    """CivicStackResponse must be JSON-serialisable for MCP tool returns."""
    resp = await fetch("pendidikan")

    data = resp.model_dump(mode="json")
    assert isinstance(data["fetched_at"], str)
    assert data["module"] == "djpb"
    assert data["status"] in [s.value for s in RecordStatus]
