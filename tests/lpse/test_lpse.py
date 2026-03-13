"""Tests for the LPSE module — VCR cassettes."""

from __future__ import annotations

import pytest
import vcr

from modules.lpse.scraper import fetch, search, search_tenders
from modules.lpse.normalizer import normalize_vendor, normalize_tender
from shared.schema import CivicStackResponse, RecordStatus

CASSETTE_DIR = "tests/lpse/cassettes"
vcr_config = vcr.VCR(
    cassette_library_dir=CASSETTE_DIR,
    record_mode="none",
    match_on=["uri", "method"],
    decode_content_encoding=True,
)


# ---------------------------------------------------------------------------
# Normalizer unit tests (no network)
# ---------------------------------------------------------------------------

def test_normalize_vendor_full():
    raw = {
        "kodeRekanan": "R-001",
        "namaRekanan": "PT CONTOH SEJAHTERA",
        "npwp": "01.234.567.8-012.000",
        "alamat": "Jl. Sudirman No.1",
        "kota": "Jakarta",
        "provinsi": "DKI Jakarta",
        "statusAktif": True,
        "jenisUsaha": "Perseroan Terbatas",
        "kualifikasi": "Menengah",
    }
    result = normalize_vendor(raw)
    assert result is not None
    assert result["vendor_name"] == "PT CONTOH SEJAHTERA"
    assert result["npwp"] == "01.234.567.8-012.000"
    assert result["is_active"] is True


def test_normalize_vendor_missing_name():
    assert normalize_vendor({"kodeRekanan": "R-001"}) is None


def test_normalize_tender_full():
    raw = {
        "kode": "T-2024-001",
        "namaPaket": "Pengadaan Alat Kesehatan",
        "namaSatker": "Rumah Sakit Umum Pusat",
        "tahapTender": "Pemasukan Penawaran",
        "metodePengadaan": "Tender",
        "nilaiPagu": 1000000000,
        "nilaiHPS": 950000000,
        "statusTender": "Aktif",
        "sumberDana": "APBN",
    }
    result = normalize_tender(raw)
    assert result is not None
    assert result["tender_name"] == "Pengadaan Alat Kesehatan"
    assert result["ceiling_value"] == 1000000000.0
    assert result["hps_value"] == 950000000.0


def test_normalize_tender_missing_name():
    assert normalize_tender({"kode": "T-001"}) is None


# ---------------------------------------------------------------------------
# Scraper tests — VCR replays
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_vendor_found():
    with vcr_config.use_cassette("vendor_found.yaml"):
        resp = await fetch("PT Garuda Indonesia")
    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.status == RecordStatus.ACTIVE
    assert resp.module == "lpse"
    assert resp.result["vendor_name"] == "PT GARUDA INDONESIA (PERSERO) TBK"
    assert resp.result["npwp"] == "01.000.013.0-051.000"
    assert resp.confidence == 1.0  # all 5 portals responded


@pytest.mark.asyncio
async def test_fetch_vendor_not_found():
    with vcr_config.use_cassette("vendor_not_found.yaml"):
        resp = await fetch("PERUSAHAAN TIDAK ADA")
    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_search_tenders():
    with vcr_config.use_cassette("tender_search.yaml"):
        results = await search_tenders("pengadaan server")
    assert len(results) == 2
    assert all(r.module == "lpse" for r in results)
    assert results[0].result["tender_name"] == "Pengadaan Server dan Infrastruktur Jaringan"
    assert results[0].result["ceiling_value"] == 5000000000.0


@pytest.mark.asyncio
async def test_partial_results_reduce_confidence():
    """When 2 of 5 portals return 503, confidence should be 0.6."""
    with vcr_config.use_cassette("partial_results.yaml"):
        resp = await fetch("PT Telkom")
    assert resp.found is True
    assert resp.confidence == 0.6  # 3/5 portals succeeded
    assert "PU" in resp.result["portal_errors"]
    assert "Kemenkeu" in resp.result["portal_errors"]


@pytest.mark.asyncio
async def test_response_json_serializable():
    with vcr_config.use_cassette("vendor_found.yaml"):
        resp = await fetch("PT Garuda Indonesia")
    data = resp.model_dump(mode="json")
    assert data["module"] == "lpse"
    assert isinstance(data["fetched_at"], str)
