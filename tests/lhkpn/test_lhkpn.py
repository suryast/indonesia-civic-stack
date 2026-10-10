"""Tests for the LHKPN module — mocked browser boundary + normalizer unit tests."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from civic_stack.lhkpn import scraper
from civic_stack.lhkpn.normalizer import normalize_declaration, normalize_search_result
from civic_stack.lhkpn.scraper import fetch, search
from civic_stack.shared.schema import CivicStackResponse, RecordStatus

# ---------------------------------------------------------------------------
# Normalizer unit tests
# ---------------------------------------------------------------------------


def test_normalize_declaration_full():
    raw = {
        "nama": "SRI MULYANI INDRAWATI",
        "jabatan": "Menteri Keuangan",
        "instansi": "Kementerian Keuangan",
        "tahun_laporan": "2023",
        "total_harta": 58000000000,
        "total_hutang": 0,
        "harta_bersih": 58000000000,
        "harta_tidak_bergerak": 30000000000,
        "harta_bergerak": 10000000000,
        "surat_berharga": 8000000000,
        "kas_setara_kas": 5000000000,
        "harta_lainnya": 5000000000,
    }
    result = normalize_declaration(raw, query="Sri Mulyani")
    assert result["official_name"] == "SRI MULYANI INDRAWATI"
    assert result["position"] == "Menteri Keuangan"
    assert result["total_assets_idr"] == 58000000000
    assert result["net_assets_idr"] == 58000000000
    assert result["asset_breakdown"]["immovable_property_idr"] == 30000000000
    assert result["_confidence"] >= 0.8


def test_normalize_declaration_computes_net():
    raw = {
        "nama": "TEST OFFICIAL",
        "total_harta": 10000000000,
        "total_hutang": 2000000000,
    }
    result = normalize_declaration(raw, query="Test Official")
    assert result["net_assets_idr"] == 8000000000


def test_normalize_declaration_idr_string():
    raw = {
        "nama": "PEJABAT CONTOH",
        "total_harta": "Rp 5.500.000.000",
    }
    result = normalize_declaration(raw, query="Pejabat Contoh")
    assert result["total_assets_idr"] == 5500000000


def test_normalize_search_result():
    raw = {
        "nama": "BUDI GUNAWAN",
        "jabatan": "Kepala BIN",
        "instansi": "Badan Intelijen Negara",
        "tahun_laporan": "2023",
    }
    rec = normalize_search_result(raw)
    assert rec["official_name"] == "BUDI GUNAWAN"
    assert rec["position"] == "Kepala BIN"
    assert rec["declaration_year"] == "2023"


def test_confidence_exact_name():
    raw = {"nama": "BUDI GUNAWAN"}
    result = normalize_declaration(raw, query="BUDI GUNAWAN")
    assert result["_confidence"] == 1.0


def test_confidence_partial_match():
    raw = {"nama": "BUDI GUNAWAN SADIKIN"}
    result = normalize_declaration(raw, query="Budi")
    assert result["_confidence"] >= 0.5


# VCR cannot intercept Playwright; fixtures represent browser table rows.
@pytest.fixture(autouse=True)
def no_live_browser(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "playwright.async_api",
        SimpleNamespace(
            async_playwright=MagicMock(
                side_effect=AssertionError("Live Playwright forbidden in unit tests")
            )
        ),
    )


@pytest.fixture
def browser_search(monkeypatch):
    mocked = AsyncMock(return_value=[])
    monkeypatch.setattr(scraper, "_playwright_search", mocked)
    return mocked


@pytest.fixture
def table_row():
    return {
        "nama": "BUDI GUNAWAN",
        "jabatan": "Kepala BIN",
        "lembaga": "BIN",
        "unit_kerja": "Pusat",
        "tanggal_lapor": "31/12/2023",
        "year": "2023",
        "jenis_laporan": "Periodik",
        "total_harta": "Rp.45.000.000.000",
        "report_id": "fixture-report",
        "download_id": "fixture-download",
    }


@pytest.mark.asyncio
async def test_fetch_official_found(browser_search, table_row):
    browser_search.return_value = [table_row]
    resp = await fetch("Budi Gunawan")
    browser_search.assert_awaited_once_with(name="Budi Gunawan")
    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.status == RecordStatus.ACTIVE
    assert resp.module == "lhkpn"
    assert resp.result["official_name"] == "BUDI GUNAWAN"
    assert resp.result["position"] == "Kepala BIN"
    assert resp.result["total_assets_idr"] == 45000000000
    assert resp.result["report_id"] == "fixture-report"
    assert resp.result["declaration_year"] == "2023"
    assert resp.raw["table_row"] == table_row


@pytest.mark.asyncio
async def test_fetch_official_not_found(browser_search):
    resp = await fetch("Pejabat Tidak Ada")
    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_search_returns_multiple(browser_search, table_row):
    names = ["SRI MULYANI INDRAWATI", "FIXTURE OFFICIAL TWO", "FIXTURE OFFICIAL THREE"]
    browser_search.return_value = [dict(table_row, nama=name) for name in names]
    results = await search("Menteri Keuangan")
    browser_search.assert_awaited_once_with(name="Menteri Keuangan")
    assert len(results) == 3
    assert all(r.module == "lhkpn" and r.found for r in results)
    assert [r.result["official_name"] for r in results] == names


@pytest.mark.asyncio
async def test_response_json_serializable(browser_search, table_row):
    browser_search.return_value = [table_row]
    data = (await fetch("Budi Gunawan")).model_dump(mode="json")
    assert data["module"] == "lhkpn"
    assert isinstance(data["fetched_at"], str)


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [ImportError("missing browser"), RuntimeError("browser failed")])
async def test_fetch_browser_failure_returns_error(browser_search, error):
    browser_search.side_effect = error
    resp = await fetch("Fixture Official")
    assert resp.found is False
    assert resp.status == RecordStatus.ERROR
    assert resp.result["detail"]


@pytest.mark.asyncio
async def test_search_browser_failure_is_empty(browser_search):
    browser_search.side_effect = RuntimeError("browser failed")
    assert await search("Fixture Official") == []


@pytest.mark.asyncio
async def test_browser_navigation_failure_is_error(monkeypatch):
    page = AsyncMock()
    page.goto.side_effect = RuntimeError("offline navigation failure")
    context = AsyncMock()
    context.new_page.return_value = page
    browser = AsyncMock()
    browser.new_context.return_value = context
    playwright = MagicMock()
    playwright.chromium.launch = AsyncMock(return_value=browser)
    manager = AsyncMock()
    manager.__aenter__.return_value = playwright
    monkeypatch.setitem(
        sys.modules,
        "playwright.async_api",
        SimpleNamespace(async_playwright=MagicMock(return_value=manager)),
    )
    resp = await fetch("Fixture Official")
    assert resp.status == RecordStatus.ERROR
    assert "offline navigation failure" in resp.result["detail"]
    browser.close.assert_awaited_once()
