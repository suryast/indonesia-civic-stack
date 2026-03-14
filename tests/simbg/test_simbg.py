"""Tests for the SIMBG module — VCR cassettes + normalizer unit tests."""

from __future__ import annotations

import pytest
import vcr

from civic_stack.shared.schema import CivicStackResponse, RecordStatus
from civic_stack.simbg.normalizer import normalize_permit, normalize_search_result
from civic_stack.simbg.scraper import fetch

CASSETTE_DIR = "tests/simbg/cassettes"
vcr_config = vcr.VCR(
    cassette_library_dir=CASSETTE_DIR,
    record_mode="none",
    match_on=["uri", "method"],
    decode_compressed_response=True,
)


# ---------------------------------------------------------------------------
# Normalizer unit tests
# ---------------------------------------------------------------------------


def test_normalize_permit_full():
    raw = {
        "nomor_pbg": "PBG-JKT-2024-001234",
        "jenis_izin": "Persetujuan Bangunan Gedung (PBG)",
        "nama_pemilik": "PT TOWER BERSAMA",
        "alamat_bangunan": "Jl. Sudirman No. 1",
        "kota": "Jakarta Pusat",
        "provinsi": "DKI Jakarta",
        "luas_bangunan": "45000",
        "jumlah_lantai": "28",
        "fungsi_bangunan": "Perkantoran",
        "status_pbg": "Berlaku",
        "tanggal_terbit": "2024-03-15",
        "instansi_penerbit": "Dinas Cipta Karya DKI",
    }
    result = normalize_permit(raw)
    assert result is not None
    assert result["permit_number"] == "PBG-JKT-2024-001234"
    assert result["owner_name"] == "PT TOWER BERSAMA"
    assert result["floor_area_m2"] == 45000.0
    assert result["floor_count"] == 28.0
    assert result["permit_status"] == "Berlaku"


def test_normalize_permit_legacy_imb():
    raw = {
        "nomor_imb": "IMB-2020-12345",
        "alamat": "Jl. Gatot Subroto No. 5",
        "kota": "Bandung",
    }
    result = normalize_permit(raw)
    assert result is not None
    assert result["permit_number"] == "IMB-2020-12345"


def test_normalize_permit_no_address_or_number():
    assert normalize_permit({"kota": "Jakarta"}) is None


def test_normalize_search_result():
    raw = {
        "nomor_pbg": "PBG-SBY-2023-555",
        "alamat_bangunan": "Jl. Pemuda No. 10",
        "kota": "Surabaya",
        "status_pbg": "Berlaku",
    }
    result = normalize_search_result(raw)
    assert result is not None
    assert result["permit_number"] == "PBG-SBY-2023-555"
    assert result["city"] == "Surabaya"


# ---------------------------------------------------------------------------
# Scraper tests — VCR replays
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_permit_found():
    with vcr_config.use_cassette("permit_found.yaml"):
        resp = await fetch("Jl. Sudirman No. 1")
    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.status == RecordStatus.ACTIVE
    assert resp.module == "simbg"
    assert resp.result["permit_number"] == "PBG-JKT-2024-001234"
    assert resp.result["owner_name"] == "PT TOWER BERSAMA INFRASTRUCTURE TBK"
    assert resp.result["floor_area_m2"] == 45000.0
    assert resp.result["permit_status"] == "Berlaku"


@pytest.mark.asyncio
async def test_fetch_permit_not_found():
    with vcr_config.use_cassette("permit_not_found.yaml"):
        resp = await fetch("Alamat Tidak Ada XYZ999")
    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_response_json_serializable():
    with vcr_config.use_cassette("permit_found.yaml"):
        resp = await fetch("Jl. Sudirman No. 1")
    data = resp.model_dump(mode="json")
    assert data["module"] == "simbg"
    assert isinstance(data["fetched_at"], str)
