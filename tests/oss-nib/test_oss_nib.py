"""Tests for the OSS-NIB module — HTML fixtures + monkeypatched Playwright."""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.oss_nib.normalizer import normalize_nib_page, normalize_search_results
from shared.schema import CivicStackResponse, RecordStatus

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_normalize_nib_found():
    resp = normalize_nib_page(_load("nib_found.html"), query="PT Gojek Indonesia",
                               source_url="https://oss.go.id/informasi/pencarian-nib")
    assert resp.found is True
    assert resp.status == RecordStatus.ACTIVE
    assert resp.module == "oss_nib"
    assert resp.result["nib"] == "8120001234567"
    assert resp.result["company_name"] == "PT GOJEK INDONESIA"
    assert resp.result["risk_level"] == "Menengah Tinggi"
    assert resp.result["kbli_code"] == "49431"


def test_normalize_nib_not_found():
    resp = normalize_nib_page(_load("nib_not_found.html"), query="unknown",
                               source_url="https://oss.go.id/informasi/pencarian-nib")
    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND


def test_normalize_search_results():
    results = normalize_search_results(_load("search_results.html"),
                                        source_url="https://oss.go.id/informasi/pencarian-nib")
    assert len(results) == 2
    assert all(r.module == "oss_nib" for r in results)
    assert results[0].result["company_name"] == "PT GOJEK INDONESIA"


def test_confidence_exact_nib():
    resp = normalize_nib_page(_load("nib_found.html"), query="8120001234567",
                               source_url="https://oss.go.id/informasi/pencarian-nib")
    assert resp.confidence == 1.0


def test_response_json_serializable():
    resp = normalize_nib_page(_load("nib_found.html"), query="PT Gojek Indonesia",
                               source_url="https://oss.go.id/informasi/pencarian-nib")
    data = resp.model_dump(mode="json")
    assert data["module"] == "oss_nib"
    assert isinstance(data["fetched_at"], str)


@pytest.mark.asyncio
async def test_fetch_monkeypatched(monkeypatch):
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock, MagicMock

    @asynccontextmanager
    async def mock_new_page(*args, **kwargs):
        page = AsyncMock()
        page.goto = AsyncMock()
        page.content = AsyncMock(return_value=_load("nib_found.html"))
        page.query_selector = AsyncMock(return_value=MagicMock(
            fill=AsyncMock(), press=AsyncMock(), click=AsyncMock()))
        page.wait_for_load_state = AsyncMock()
        yield page

    monkeypatch.setattr("modules.oss_nib.scraper.new_page", mock_new_page)
    monkeypatch.setattr("modules.oss_nib.scraper.wait_for_results", AsyncMock(return_value=True))

    from modules.oss_nib.scraper import fetch
    resp = await fetch("PT Gojek Indonesia")
    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
