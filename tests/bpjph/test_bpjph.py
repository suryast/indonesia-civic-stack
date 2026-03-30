"""
Tests for the BPJPH module.

The scraper uses httpx REST API calls to cmsbl.halal.go.id.
Tests monkeypatch the HTTP layer and inject JSON fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from civic_stack.bpjph.normalizer import normalize_cert_page, normalize_search_results
from civic_stack.shared.schema import CivicStackResponse, RecordStatus

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load(filename: str) -> str:
    return (FIXTURE_DIR / filename).read_text(encoding="utf-8")


def _load_json(filename: str) -> dict:
    return json.loads((FIXTURE_DIR / filename).read_text(encoding="utf-8"))


# ── Normalizer unit tests (from HTML fixtures — backwards compat) ─────────────


def test_normalize_cert_found():
    html = _load("cert_found.html")
    resp = normalize_cert_page(
        html,
        cert_no="ID00110019882120240001",
        source_url="https://sertifikasi.halal.go.id/sertifikat/publik",
    )

    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.status == RecordStatus.ACTIVE
    assert resp.module == "bpjph"
    assert resp.confidence == 1.0
    assert resp.result is not None
    assert resp.result["company"] == "PT INDOFOOD SUKSES MAKMUR TBK"
    assert resp.result["cert_no"] == "ID00110019882120240001"
    assert resp.result["issuer"] == "BPJPH"
    assert isinstance(resp.result["product_list"], list)
    assert len(resp.result["product_list"]) == 3


def test_normalize_cert_not_found():
    html = _load("cert_not_found.html")
    resp = normalize_cert_page(
        html,
        cert_no="INVALID-999",
        source_url="https://sertifikasi.halal.go.id/sertifikat/publik",
    )

    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND


def test_normalize_search_results():
    html = _load("search_results.html")
    results = normalize_search_results(
        html,
        source_url="https://sertifikasi.halal.go.id/sertifikat/publik",
    )

    assert isinstance(results, list)
    assert len(results) == 2
    for r in results:
        assert isinstance(r, CivicStackResponse)
        assert r.found is True
        assert r.module == "bpjph"
        assert r.confidence == 0.8


def test_normalize_search_result_fields():
    html = _load("search_results.html")
    results = normalize_search_results(
        html,
        source_url="https://sertifikasi.halal.go.id/sertifikat/publik",
    )

    first = results[0]
    assert first.result is not None
    assert "cert_no" in first.result or "no. sertifikat" in first.result or first.result


def test_cert_debug_includes_raw():
    html = _load("cert_found.html")
    resp = normalize_cert_page(
        html,
        cert_no="ID00110019882120240001",
        source_url="https://sertifikasi.halal.go.id/sertifikat/publik",
        debug=True,
    )
    assert resp.raw is not None
    assert isinstance(resp.raw, dict)


def test_response_json_serializable():
    html = _load("cert_found.html")
    resp = normalize_cert_page(
        html,
        cert_no="ID00110019882120240001",
        source_url="https://sertifikasi.halal.go.id/sertifikat/publik",
    )
    data = resp.model_dump(mode="json")
    assert data["module"] == "bpjph"
    assert isinstance(data["fetched_at"], str)
    assert data["status"] in [s.value for s in RecordStatus]


# ── REST API scraper tests (monkeypatched httpx) ─────────────────────────────


def _mock_response(data: dict, status_code: int = 200):
    """Create a mock httpx response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = data
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture
def cert_api_response():
    """Sample API response for a certificate fetch."""
    return {
        "data": [
            {
                "no_sertifikat": "ID00110019882120240001",
                "nama_perusahaan": "PT INDOFOOD SUKSES MAKMUR TBK",
                "nama_produk": "Indomie Goreng, Indomie Soto, Supermi",
                "status_sertifikat": "Berlaku",
                "tgl_terbit": "2024-01-15",
                "tgl_kadaluarsa": "2028-01-15",
            }
        ]
    }


@pytest.fixture
def search_api_response():
    """Sample API response for a product search."""
    return {
        "data": [
            {
                "no_sertifikat": "ID00110019882120240001",
                "nama_perusahaan": "PT INDOFOOD",
                "nama_produk": "Indomie Goreng",
                "status_sertifikat": "Berlaku",
            },
            {
                "no_sertifikat": "ID00110019882120240002",
                "nama_perusahaan": "PT INDOFOOD",
                "nama_produk": "Supermi",
                "status_sertifikat": "Berlaku",
            },
        ]
    }


@pytest.mark.asyncio
async def test_fetch_uses_rest_api(monkeypatch, cert_api_response):
    """fetch() calls cmsbl.halal.go.id REST API and normalizes the result."""
    from contextlib import asynccontextmanager

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_mock_response(cert_api_response))

    @asynccontextmanager
    async def mock_civic_client(**kwargs):
        yield mock_client

    monkeypatch.setattr("civic_stack.bpjph.scraper.civic_client", mock_civic_client)

    from civic_stack.bpjph.scraper import fetch

    resp = await fetch("ID00110019882120240001")

    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.module == "bpjph"
    assert resp.confidence == 1.0
    assert resp.result["cert_no"] == "ID00110019882120240001"
    assert resp.result["company"] == "PT INDOFOOD SUKSES MAKMUR TBK"


@pytest.mark.asyncio
async def test_fetch_not_found(monkeypatch):
    """fetch() returns not_found when API returns no records."""
    from contextlib import asynccontextmanager

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_mock_response({"data": []}))

    @asynccontextmanager
    async def mock_civic_client(**kwargs):
        yield mock_client

    monkeypatch.setattr("civic_stack.bpjph.scraper.civic_client", mock_civic_client)

    from civic_stack.bpjph.scraper import fetch

    resp = await fetch("NONEXISTENT-999")

    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_search_returns_multiple(monkeypatch, search_api_response):
    """search() returns a list of CivicStackResponse for matches."""
    from contextlib import asynccontextmanager

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=_mock_response(search_api_response))

    @asynccontextmanager
    async def mock_civic_client(**kwargs):
        yield mock_client

    monkeypatch.setattr("civic_stack.bpjph.scraper.civic_client", mock_civic_client)

    from civic_stack.bpjph.scraper import search

    results = await search("indomie")

    assert isinstance(results, list)
    assert len(results) == 2
    for r in results:
        assert r.found is True
        assert r.module == "bpjph"


@pytest.mark.asyncio
async def test_fetch_handles_network_error(monkeypatch):
    """fetch() gracefully handles network failures."""
    from contextlib import asynccontextmanager

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("Connection timeout"))

    @asynccontextmanager
    async def mock_civic_client(**kwargs):
        yield mock_client

    monkeypatch.setattr("civic_stack.bpjph.scraper.civic_client", mock_civic_client)

    from civic_stack.bpjph.scraper import fetch

    resp = await fetch("ID00110019882120240001")

    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND
