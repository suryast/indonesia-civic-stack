"""Tests for the OJK module — monkeypatched (portal scraping, no VCR)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import httpx
import pytest

from civic_stack.ojk.scraper import check_waspada, fetch
from civic_stack.shared.schema import CivicStackResponse, RecordStatus


INSTITUTION_HTML = """
<html><body>
<table class="table table-bordered">
  <thead><tr><th>Nama</th><th>No. Izin</th><th>Jenis</th><th>Status</th></tr></thead>
  <tbody>
    <tr>
      <td>PT AKULAKU FINANCE INDONESIA</td>
      <td>KEP-249/NB.11/2018</td>
      <td>Perusahaan Pembiayaan</td>
      <td>Aktif</td>
    </tr>
  </tbody>
</table>
</body></html>
"""

NOT_FOUND_HTML = """
<html><body>
<table class="table table-bordered">
  <thead><tr><th>Nama</th><th>No. Izin</th></tr></thead>
  <tbody></tbody>
</table>
</body></html>
"""

WASPADA_JSON = json.dumps({
    "data": [
        {
            "nama_entitas": "PT UNTUNG BERLIPAT INVESTASI",
            "jenis_kegiatan": "Investasi Ilegal",
            "keterangan": "Tidak terdaftar di OJK",
        }
    ],
    "recordsTotal": 1,
})


def _mock_response(body: str, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        text=body,
        request=httpx.Request("GET", "https://www.ojk.go.id"),
    )


@pytest.mark.asyncio
async def test_fetch_institution_found(monkeypatch):
    mock_fetch = AsyncMock(return_value=_mock_response(INSTITUTION_HTML))
    monkeypatch.setattr("civic_stack.ojk.scraper.fetch_with_retry", mock_fetch)

    resp = await fetch("Akulaku")
    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.status == RecordStatus.ACTIVE
    assert resp.module == "ojk"
    assert "AKULAKU" in resp.result["institution_name"].upper()


@pytest.mark.asyncio
async def test_fetch_institution_not_found(monkeypatch):
    mock_fetch = AsyncMock(return_value=_mock_response(NOT_FOUND_HTML))
    monkeypatch.setattr("civic_stack.ojk.scraper.fetch_with_retry", mock_fetch)

    resp = await fetch("LEMBAGA TIDAK ADA")
    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_waspada_found(monkeypatch):
    mock_fetch = AsyncMock(return_value=_mock_response(WASPADA_JSON))
    monkeypatch.setattr("civic_stack.ojk.scraper.fetch_with_retry", mock_fetch)

    resp = await check_waspada("Untung Berlipat")
    assert resp.found is True
    assert resp.status == RecordStatus.SUSPENDED
    assert resp.result["on_waspada_list"] is True


@pytest.mark.asyncio
async def test_response_json_serializable(monkeypatch):
    mock_fetch = AsyncMock(return_value=_mock_response(INSTITUTION_HTML))
    monkeypatch.setattr("civic_stack.ojk.scraper.fetch_with_retry", mock_fetch)

    resp = await fetch("Akulaku")
    data = resp.model_dump(mode="json")
    assert data["module"] == "ojk"
    assert isinstance(data["fetched_at"], str)
