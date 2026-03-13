"""Tests for the LHKPN module — VCR cassettes + normalizer unit tests."""

from __future__ import annotations

import pytest
import vcr

from modules.lhkpn.normalizer import normalize_declaration, normalize_search_result
from modules.lhkpn.scraper import fetch, search
from shared.schema import CivicStackResponse, RecordStatus

CASSETTE_DIR = "tests/lhkpn/cassettes"
vcr_config = vcr.VCR(
    cassette_library_dir=CASSETTE_DIR,
    record_mode="none",
    match_on=["uri", "method"],
    decode_compressed_response=True,
)


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


# ---------------------------------------------------------------------------
# Scraper tests — VCR replays
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_official_found():
    with vcr_config.use_cassette("official_found.yaml"):
        resp = await fetch("Budi Gunawan")
    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.status == RecordStatus.ACTIVE
    assert resp.module == "lhkpn"
    assert resp.result["official_name"] == "BUDI GUNAWAN"
    assert resp.result["position"] == "Kepala BIN"
    assert resp.result["total_assets_idr"] == 45000000000
    assert resp.result["net_assets_idr"] == 40000000000
    assert "asset_breakdown" in resp.result
    assert resp.result["asset_breakdown"]["immovable_property_idr"] == 30000000000


@pytest.mark.asyncio
async def test_fetch_official_not_found():
    with vcr_config.use_cassette("official_not_found.yaml"):
        resp = await fetch("Pejabat Tidak Ada")
    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_search_returns_multiple():
    with vcr_config.use_cassette("search_multi.yaml"):
        results = await search("Menteri Keuangan")
    assert len(results) == 3
    assert all(r.module == "lhkpn" for r in results)
    assert results[0].result["official_name"] == "SRI MULYANI INDRAWATI"


@pytest.mark.asyncio
async def test_response_json_serializable():
    with vcr_config.use_cassette("official_found.yaml"):
        resp = await fetch("Budi Gunawan")
    data = resp.model_dump(mode="json")
    assert data["module"] == "lhkpn"
    assert isinstance(data["fetched_at"], str)
