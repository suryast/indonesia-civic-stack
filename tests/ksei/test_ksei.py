"""
Tests for the KSEI module — monkeypatched HTTP responses (no live calls).

The scraper fetches server-rendered HTML from web.ksei.co.id via
fetch_with_retry(); tests stub that boundary with realistic HTML so the
BeautifulSoup parsing paths are exercised too.
"""

from __future__ import annotations

import pytest

from civic_stack.ksei.scraper import (
    fetch,
    get_latest_statistics_url,
    get_statistics_links,
    search,
)
from civic_stack.shared.schema import CivicStackResponse, RecordStatus

# Securities listing table: code | name | type | issuer (≥4 cells per row)
SECURITIES_HTML = """
<html>
<body>
<table class="table">
<tr><th>Kode</th><th>Nama Efek</th><th>Jenis</th><th>Penerbit</th></tr>
<tr>
    <td>BBCA</td>
    <td>Bank Central Asia Tbk</td>
    <td>Saham</td>
    <td>PT Bank Central Asia Tbk</td>
</tr>
<tr>
    <td>BBRI</td>
    <td>Bank Rakyat Indonesia (Persero) Tbk</td>
    <td>Saham</td>
    <td>PT Bank Rakyat Indonesia (Persero) Tbk</td>
</tr>
</table>
</body>
</html>
"""

EMPTY_HTML = """
<html>
<body>
<p>Data tidak tersedia</p>
</body>
</html>
"""

STATISTICS_HTML = """
<html>
<body>
<a href="/Download/Statistik_Publik_Mei_2026.pdf">Statistik Publik Mei 2026</a>
<a href="/Download/Statistik_Publik_April_2026.pdf">Statistik Publik April 2026</a>
</body>
</html>
"""


class _MockResponse:
    def __init__(self, text: str):
        self.text = text


def _mock_fetch(monkeypatch, html: str) -> None:
    async def _fetch(*args, **kwargs):
        return _MockResponse(html)

    monkeypatch.setattr("civic_stack.ksei.scraper.fetch_with_retry", _fetch)


@pytest.mark.asyncio
async def test_search_found(monkeypatch):
    """search() matches keyword against security code and name."""
    _mock_fetch(monkeypatch, SECURITIES_HTML)

    results = await search("bank")

    assert isinstance(results, list)
    assert len(results) == 2
    assert all(isinstance(r, CivicStackResponse) for r in results)

    first = results[0]
    assert first.found is True
    assert first.module == "ksei"
    assert first.status == RecordStatus.ACTIVE
    assert first.result is not None
    assert first.result["security_code"] == "BBCA"
    assert first.result["issuer"] == "PT Bank Central Asia Tbk"


@pytest.mark.asyncio
async def test_search_by_code(monkeypatch):
    """An exact code match gets confidence 1.0."""
    _mock_fetch(monkeypatch, SECURITIES_HTML)

    results = await search("bbri")

    assert len(results) == 1
    assert results[0].result["security_code"] == "BBRI"
    assert results[0].confidence == 1.0


@pytest.mark.asyncio
async def test_search_not_found(monkeypatch):
    """search() returns an empty list when nothing matches."""
    _mock_fetch(monkeypatch, SECURITIES_HTML)

    results = await search("nonexistent")

    assert isinstance(results, list)
    assert results == []


@pytest.mark.asyncio
async def test_fetch_found(monkeypatch):
    """fetch() returns the security matching the code."""
    _mock_fetch(monkeypatch, SECURITIES_HTML)

    resp = await fetch("BBCA")

    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.module == "ksei"
    assert resp.status == RecordStatus.ACTIVE
    assert resp.result is not None
    assert resp.result["security_name"] == "Bank Central Asia Tbk"


@pytest.mark.asyncio
async def test_fetch_not_found(monkeypatch):
    """fetch() returns a NOT_FOUND envelope for an unknown code."""
    _mock_fetch(monkeypatch, EMPTY_HTML)

    resp = await fetch("ZZZZ")

    assert isinstance(resp, CivicStackResponse)
    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_statistics_links(monkeypatch):
    """get_statistics_links() parses monthly PDF links with period info."""
    _mock_fetch(monkeypatch, STATISTICS_HTML)

    links = await get_statistics_links()

    assert len(links) == 2
    assert links[0]["statistics_period"] == "Mei 2026"
    assert links[0]["download_url"].endswith("Statistik_Publik_Mei_2026.pdf")


@pytest.mark.asyncio
async def test_latest_statistics_url(monkeypatch):
    """get_latest_statistics_url() returns the first (newest) PDF link."""
    _mock_fetch(monkeypatch, STATISTICS_HTML)

    url = await get_latest_statistics_url()

    assert url == "https://web.ksei.co.id/Download/Statistik_Publik_Mei_2026.pdf"


@pytest.mark.asyncio
async def test_response_json_serializable(monkeypatch):
    """CivicStackResponse must be JSON-serialisable for MCP tool returns."""
    _mock_fetch(monkeypatch, SECURITIES_HTML)

    resp = await fetch("BBCA")

    data = resp.model_dump(mode="json")
    assert isinstance(data["fetched_at"], str)
    assert data["module"] == "ksei"
    assert data["status"] in [s.value for s in RecordStatus]
