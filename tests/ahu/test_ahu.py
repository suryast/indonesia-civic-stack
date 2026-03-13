"""
Tests for the AHU module.

Like BPJPH, AHU uses Playwright which cannot be VCR-recorded directly.
Tests run against HTML fixtures with the browser layer monkeypatched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.ahu.normalizer import normalize_company_page, normalize_search_results
from shared.schema import CivicStackResponse, RecordStatus

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load(filename: str) -> str:
    return (FIXTURE_DIR / filename).read_text(encoding="utf-8")


# ── Normalizer unit tests ─────────────────────────────────────────────────────


def test_normalize_company_found():
    html = _load("company_found.html")
    resp = normalize_company_page(
        html,
        query="PT Contoh Indonesia Tbk",
        source_url="https://ahu.go.id/pencarian/perseroan-terbatas",
    )

    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.status == RecordStatus.ACTIVE
    assert resp.module == "ahu"
    assert resp.result is not None
    assert resp.result["company_name"] == "PT CONTOH INDONESIA TBK"
    assert resp.result["registration_no"] == "AHU-0012345.AH.01.01.TAHUN2020"
    assert resp.result["legal_status"] == RecordStatus.ACTIVE.value


def test_normalize_company_directors():
    html = _load("company_found.html")
    resp = normalize_company_page(
        html,
        query="PT Contoh Indonesia Tbk",
        source_url="https://ahu.go.id/pencarian/perseroan-terbatas",
    )

    assert resp.result is not None
    directors = resp.result.get("directors", [])
    assert len(directors) == 2
    assert any(d.get("nama") == "BUDI SANTOSO" for d in directors)


def test_normalize_company_commissioners():
    html = _load("company_found.html")
    resp = normalize_company_page(
        html,
        query="PT Contoh Indonesia Tbk",
        source_url="https://ahu.go.id/pencarian/perseroan-terbatas",
    )

    assert resp.result is not None
    commissioners = resp.result.get("commissioners", [])
    assert len(commissioners) == 2
    assert any(d.get("nama") == "AHMAD YUSUF" for d in commissioners)


def test_normalize_company_not_found():
    html = _load("company_not_found.html")
    resp = normalize_company_page(
        html,
        query="PT Tidak Ada",
        source_url="https://ahu.go.id/pencarian/perseroan-terbatas",
    )

    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND


def test_normalize_search_results():
    html = _load("search_results.html")
    results = normalize_search_results(
        html,
        source_url="https://ahu.go.id/pencarian/perseroan-terbatas",
    )

    assert isinstance(results, list)
    assert len(results) == 3
    for r in results:
        assert isinstance(r, CivicStackResponse)
        assert r.found is True
        assert r.module == "ahu"
        assert r.confidence == 0.8


def test_normalize_search_result_fields():
    html = _load("search_results.html")
    results = normalize_search_results(
        html,
        source_url="https://ahu.go.id/pencarian/perseroan-terbatas",
    )

    first = results[0]
    assert first.result is not None
    assert "company_name" in first.result
    assert first.result["company_name"] == "PT CONTOH INDONESIA TBK"


def test_debug_includes_raw():
    html = _load("company_found.html")
    resp = normalize_company_page(
        html,
        query="PT Contoh Indonesia Tbk",
        source_url="https://ahu.go.id/pencarian/perseroan-terbatas",
        debug=True,
    )
    assert resp.raw is not None
    assert "directors" in resp.raw


def test_confidence_exact_match():
    html = _load("company_found.html")
    resp = normalize_company_page(
        html,
        query="PT CONTOH INDONESIA TBK",
        source_url="https://ahu.go.id/pencarian/perseroan-terbatas",
    )
    assert resp.confidence == 1.0


def test_confidence_partial_match():
    html = _load("company_found.html")
    resp = normalize_company_page(
        html,
        query="Contoh Indonesia",
        source_url="https://ahu.go.id/pencarian/perseroan-terbatas",
    )
    assert resp.confidence == 0.9


def test_response_json_serializable():
    html = _load("company_found.html")
    resp = normalize_company_page(
        html,
        query="PT Contoh Indonesia Tbk",
        source_url="https://ahu.go.id/pencarian/perseroan-terbatas",
    )
    data = resp.model_dump(mode="json")
    assert data["module"] == "ahu"
    assert isinstance(data["fetched_at"], str)
    assert data["status"] in [s.value for s in RecordStatus]


# ── Scraper integration tests (monkeypatched Playwright) ─────────────────────


@pytest.mark.asyncio
async def test_fetch_uses_normalizer(monkeypatch):
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock, MagicMock

    html_content = _load("company_found.html")

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.content = AsyncMock(return_value=html_content)
    mock_page.wait_for_load_state = AsyncMock()
    mock_page.query_selector = AsyncMock(
        return_value=MagicMock(
            fill=AsyncMock(),
            press=AsyncMock(),
            click=AsyncMock(),
        )
    )

    @asynccontextmanager
    async def mock_ahu_page(*args, **kwargs):
        yield mock_page

    monkeypatch.setattr("modules.ahu.scraper.ahu_page", mock_ahu_page)
    monkeypatch.setattr("modules.ahu.scraper.wait_for_ahu_results", AsyncMock(return_value=True))

    from modules.ahu.scraper import fetch

    resp = await fetch("PT Contoh Indonesia Tbk")

    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.module == "ahu"


@pytest.mark.asyncio
async def test_blocked_response_returns_error(monkeypatch):
    """Verify that when AHU blocks (no results rendered), we get an ERROR response."""
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.content = AsyncMock(
        return_value="<html><body>Cloudflare challenge page</body></html>"
    )
    mock_page.query_selector = AsyncMock(return_value=None)  # No search input found

    @asynccontextmanager
    async def mock_ahu_page(*args, **kwargs):
        yield mock_page

    monkeypatch.setattr("modules.ahu.scraper.ahu_page", mock_ahu_page)
    monkeypatch.setattr("modules.ahu.scraper.wait_for_ahu_results", AsyncMock(return_value=False))

    from modules.ahu.scraper import fetch

    resp = await fetch("PT Contoh Indonesia Tbk")

    assert resp.found is False
    assert resp.status == RecordStatus.ERROR
    assert resp.confidence == 0.0
