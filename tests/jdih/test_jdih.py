"""
Tests for the JDIH module — monkeypatched HTTP responses (no live API calls).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from civic_stack.jdih.scraper import fetch, search
from civic_stack.shared.schema import CivicStackResponse, RecordStatus

# Mock HTML response for a found document
FOUND_HTML = """
<html>
<body>
<table class="table">
<tr><th>Judul</th><th>Nomor</th><th>Tahun</th><th>Link</th></tr>
<tr>
    <td>Peraturan BPK tentang Audit APBN</td>
    <td>Nomor 4 Tahun 2025</td>
    <td>2025</td>
    <td><a href="/doc/peraturan-4-2025.pdf">Download PDF</a></td>
</tr>
</table>
</body>
</html>
"""

# Mock HTML response for not found
NOT_FOUND_HTML = """
<html>
<body>
<p>Tidak ada hasil yang ditemukan</p>
</body>
</html>
"""

# Mock HTML response for search results
SEARCH_RESULTS_HTML = """
<html>
<body>
<table class="table">
<tr><th>Judul</th><th>Nomor</th><th>Tahun</th><th>Link</th></tr>
<tr>
    <td>Peraturan BPK tentang Audit APBN</td>
    <td>Nomor 4 Tahun 2025</td>
    <td>2025</td>
    <td><a href="/doc/peraturan-4-2025.pdf">Download PDF</a></td>
</tr>
<tr>
    <td>Keputusan BPK tentang Audit Daerah</td>
    <td>Nomor 5 Tahun 2025</td>
    <td>2025</td>
    <td><a href="/doc/keputusan-5-2025.pdf">Download PDF</a></td>
</tr>
</table>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_search_found(monkeypatch):
    """Test search returns results when documents are found."""

    # Mock the fetch_with_retry function
    mock_response = AsyncMock()
    mock_response.text = SEARCH_RESULTS_HTML

    async def mock_fetch(*args, **kwargs):
        return mock_response

    monkeypatch.setattr("civic_stack.jdih.scraper.fetch_with_retry", mock_fetch)

    results = await search("audit", category=1)

    assert isinstance(results, list)
    assert len(results) == 2
    assert all(isinstance(r, CivicStackResponse) for r in results)

    first = results[0]
    assert first.found is True
    assert first.module == "jdih"
    assert first.status == RecordStatus.ACTIVE
    assert first.result is not None
    assert "title" in first.result or "judul" in first.result


@pytest.mark.asyncio
async def test_search_not_found(monkeypatch):
    """Test search returns NOT_FOUND when no documents match."""

    mock_response = AsyncMock()
    mock_response.text = NOT_FOUND_HTML

    async def mock_fetch(*args, **kwargs):
        return mock_response

    monkeypatch.setattr("civic_stack.jdih.scraper.fetch_with_retry", mock_fetch)

    results = await search("nonexistent")

    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0].found is False
    assert results[0].status == RecordStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_fetch_found(monkeypatch):
    """Test fetch returns document when found via search."""

    mock_response = AsyncMock()
    mock_response.text = FOUND_HTML

    async def mock_fetch(*args, **kwargs):
        return mock_response

    monkeypatch.setattr("civic_stack.jdih.scraper.fetch_with_retry", mock_fetch)

    resp = await fetch("Nomor 4 Tahun 2025")

    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.module == "jdih"
    assert resp.status == RecordStatus.ACTIVE
    assert resp.result is not None


@pytest.mark.asyncio
async def test_fetch_not_found(monkeypatch):
    """Test fetch returns NOT_FOUND when document doesn't exist."""

    mock_response = AsyncMock()
    mock_response.text = NOT_FOUND_HTML

    async def mock_fetch(*args, **kwargs):
        return mock_response

    monkeypatch.setattr("civic_stack.jdih.scraper.fetch_with_retry", mock_fetch)

    resp = await fetch("Nomor 999 Tahun 1999")

    assert isinstance(resp, CivicStackResponse)
    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_response_json_serializable(monkeypatch):
    """CivicStackResponse must be JSON-serialisable for MCP tool returns."""

    mock_response = AsyncMock()
    mock_response.text = FOUND_HTML

    async def mock_fetch(*args, **kwargs):
        return mock_response

    monkeypatch.setattr("civic_stack.jdih.scraper.fetch_with_retry", mock_fetch)

    resp = await fetch("Nomor 4 Tahun 2025")

    data = resp.model_dump(mode="json")
    assert isinstance(data["fetched_at"], str)
    assert data["module"] == "jdih"
    assert data["status"] in [s.value for s in RecordStatus]
