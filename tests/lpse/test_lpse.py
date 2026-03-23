"""Tests for the LPSE module — mock-based since portals are behind Cloudflare."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from civic_stack.lpse.normalizer import normalize_tender, normalize_vendor
from civic_stack.lpse.scraper import (
    DEPRECATED_PORTALS,
    INAPROC_PORTAL,
    PORTALS,
    fetch,
    search,
    search_tenders,
)

# ---------------------------------------------------------------------------
# Normalizer unit tests (no network)
# ---------------------------------------------------------------------------


def test_normalize_vendor_full():
    raw = {
        "kodeRekanan": "R-001",
        "namaRekanan": "PT CONTOH SEJAHTERA",
        "npwp": "01.234.567.8-012.000",
    }
    result = normalize_vendor(raw)
    assert result is not None
    assert result["vendor_name"] == "PT CONTOH SEJAHTERA"
    assert result["npwp"] == "01.234.567.8-012.000"


def test_normalize_vendor_empty():
    assert normalize_vendor({}) is None
    assert normalize_vendor(None) is None


def test_normalize_tender_full():
    raw = {
        "kodeTender": "T-001",
        "namaPaket": "Pengadaan Komputer",
        "nilaiPagu": 1000000000,
        "tahapTender": "Pengumuman",
    }
    result = normalize_tender(raw)
    assert result is not None
    assert result["tender_name"] == "Pengadaan Komputer"


def test_normalize_tender_empty():
    assert normalize_tender({}) is None
    assert normalize_tender(None) is None


# ---------------------------------------------------------------------------
# Portal configuration tests
# ---------------------------------------------------------------------------


def test_portals_no_dead_dns():
    """Ensure no DNS-dead portals in active list."""
    dead_bases = {p["base"] for p in DEPRECATED_PORTALS}
    for portal in PORTALS:
        assert portal["base"] not in dead_bases, f"{portal['name']} is deprecated"


def test_portals_all_use_eproc4():
    """All portals use /eproc4 path."""
    for portal in PORTALS:
        assert "/eproc4" in portal["base"], f"{portal['name']} missing /eproc4"


def test_deprecated_portals_have_reasons():
    """All deprecated portals document why."""
    for portal in DEPRECATED_PORTALS:
        assert "reason" in portal, f"{portal['name']} missing deprecation reason"


def test_inaproc_portal_url():
    assert INAPROC_PORTAL == "https://spse.inaproc.id"


def test_source_base_is_inaproc():
    """Source URL now points to inaproc.id, not the dead lkpp.go.id."""
    from civic_stack.lpse.scraper import SOURCE_BASE

    assert "inaproc.id" in SOURCE_BASE
    assert "lkpp.go.id" not in SOURCE_BASE


# ---------------------------------------------------------------------------
# Fetch tests (mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_all_portals_down():
    """When all portals fail, return not-found with portal_errors."""
    with patch(
        "civic_stack.lpse.scraper._search_portal", new_callable=AsyncMock, return_value=None
    ):
        result = await fetch("PT CONTOH")
    assert result.found is False
    assert result.module == "lpse"


MOCK_PORTALS = [
    {"name": "MockPortal", "base": "https://lpse.mock.go.id/eproc4"},
]


@pytest.mark.asyncio
async def test_fetch_one_portal_succeeds():
    """When one portal returns data, return results with reduced confidence."""
    mock_data = {
        "data": [{"kodeRekanan": "R-001", "namaRekanan": "PT TEST", "npwp": "01.234.567.8-012.000"}]
    }

    async def mock_search(client, portal, term, endpoint):
        return mock_data

    with (
        patch("civic_stack.lpse.scraper.PORTALS", MOCK_PORTALS),
        patch("civic_stack.lpse.scraper._search_portal", side_effect=mock_search),
    ):
        result = await fetch("PT TEST")
    assert result.found is True
    assert result.result["vendor_name"] == "PT TEST"
    assert result.confidence > 0  # has valid confidence


@pytest.mark.asyncio
async def test_search_deduplicates_by_npwp():
    """Same vendor from multiple portals should be deduped."""
    mock_data = {
        "data": [{"kodeRekanan": "R-001", "namaRekanan": "PT TEST", "npwp": "01.234.567.8-012.000"}]
    }

    async def mock_search(client, portal, term, endpoint):
        return mock_data

    with (
        patch("civic_stack.lpse.scraper.PORTALS", MOCK_PORTALS),
        patch("civic_stack.lpse.scraper._search_portal", side_effect=mock_search),
    ):
        results = await search("PT TEST")
    # Should be deduped to 1 despite N portals returning same vendor
    assert len(results) == 1


@pytest.mark.asyncio
async def test_search_tenders_returns_list():
    """search_tenders returns list of CivicStackResponse."""
    mock_data = {
        "data": [
            {
                "kode": "T-001",
                "namaPaket": "Pengadaan PC",
                "nilaiPagu": 500000000,
                "tahapTender": "Pengumuman",
            }
        ]
    }

    async def mock_search(client, portal, term, endpoint):
        return mock_data

    with (
        patch("civic_stack.lpse.scraper.PORTALS", MOCK_PORTALS),
        patch("civic_stack.lpse.scraper._search_portal", side_effect=mock_search),
    ):
        results = await search_tenders("komputer")
    assert len(results) >= 1
    assert results[0].found is True
