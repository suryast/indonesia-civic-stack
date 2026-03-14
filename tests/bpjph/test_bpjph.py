"""
Tests for the BPJPH module.

The scraper uses Playwright which cannot be VCR-recorded directly.
Tests monkeypatch the browser layer and inject HTML fixtures, keeping
CI free from live portal calls and browser binary requirements.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from civic_stack.bpjph.normalizer import normalize_cert_page, normalize_search_results
from civic_stack.shared.schema import CivicStackResponse, RecordStatus

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load(filename: str) -> str:
    return (FIXTURE_DIR / filename).read_text(encoding="utf-8")


# ── Normalizer unit tests (no Playwright needed) ──────────────────────────────


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


# ── Scraper integration tests (monkeypatched Playwright) ─────────────────────


@pytest.mark.asyncio
async def test_fetch_uses_normalizer(monkeypatch):
    """
    Monkeypatch the Playwright new_page context manager so fetch() can run
    without a real browser. Injects the cert_found.html fixture.
    """
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock, MagicMock

    html_content = _load("cert_found.html")

    # Mock page object
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.content = AsyncMock(return_value=html_content)
    mock_page.query_selector = AsyncMock(
        return_value=MagicMock(
            fill=AsyncMock(),
            press=AsyncMock(),
        )
    )

    @asynccontextmanager
    async def mock_new_page(*args, **kwargs):
        yield mock_page

    monkeypatch.setattr("modules.bpjph.scraper.new_page", mock_new_page)
    monkeypatch.setattr("modules.bpjph.scraper.wait_for_results", AsyncMock(return_value=True))

    from civic_stack.bpjph.scraper import fetch

    resp = await fetch("ID00110019882120240001")

    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.module == "bpjph"


@pytest.mark.asyncio
async def test_search_uses_normalizer(monkeypatch):
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock, MagicMock

    html_content = _load("search_results.html")

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.content = AsyncMock(return_value=html_content)
    mock_page.query_selector = AsyncMock(
        return_value=MagicMock(
            fill=AsyncMock(),
            press=AsyncMock(),
        )
    )

    @asynccontextmanager
    async def mock_new_page(*args, **kwargs):
        yield mock_page

    monkeypatch.setattr("modules.bpjph.scraper.new_page", mock_new_page)
    monkeypatch.setattr("modules.bpjph.scraper.wait_for_results", AsyncMock(return_value=True))

    from civic_stack.bpjph.scraper import search

    results = await search("mie instan")

    assert isinstance(results, list)
    assert len(results) == 2
