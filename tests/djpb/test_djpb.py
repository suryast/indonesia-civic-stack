"""
Tests for the DJPB module — monkeypatched HTTP responses (no live API calls).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from civic_stack.djpb.scraper import fetch, search
from civic_stack.shared.schema import CivicStackResponse, RecordStatus


# Mock HTML response for budget data page
FOUND_HTML = """
<html>
<body>
<table class="table">
<tr><th>Tahun Anggaran</th><th>Realisasi</th><th>Download</th></tr>
<tr>
    <td>2025</td>
    <td>Rp 1.250.000.000.000</td>
    <td><a href="/apbn/2025-realisasi.pdf">Download</a></td>
</tr>
</table>
</body>
</html>
"""

# Mock HTML response for not found
NOT_FOUND_HTML = """
<html>
<body>
<p>Data tidak ditemukan</p>
</body>
</html>
"""

# Mock HTML response for search results
SEARCH_RESULTS_HTML = """
<html>
<body>
<table class="table">
<tr><th>Tahun</th><th>Kategori</th><th>Realisasi</th><th>Download</th></tr>
<tr>
    <td>2025</td>
    <td>APBN Realisasi Q1</td>
    <td>Rp 350.000.000.000</td>
    <td><a href="/apbn/2025-q1.pdf">Download</a></td>
</tr>
<tr>
    <td>2025</td>
    <td>APBN Realisasi Q2</td>
    <td>Rp 725.000.000.000</td>
    <td><a href="/apbn/2025-q2.pdf">Download</a></td>
</tr>
</table>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_search_found(monkeypatch):
    """Test search returns results when budget data is found."""
    
    # Mock the fetch_with_retry function
    mock_response = AsyncMock()
    mock_response.text = SEARCH_RESULTS_HTML
    
    async def mock_fetch(*args, **kwargs):
        return mock_response
    
    monkeypatch.setattr("civic_stack.djpb.scraper.fetch_with_retry", mock_fetch)
    
    results = await search("2025")
    
    assert isinstance(results, list)
    assert len(results) == 2
    assert all(isinstance(r, CivicStackResponse) for r in results)
    
    first = results[0]
    assert first.found is True
    assert first.module == "djpb"
    assert first.status == RecordStatus.ACTIVE
    assert first.result is not None


@pytest.mark.asyncio
async def test_search_not_found(monkeypatch):
    """Test search returns NOT_FOUND when no data matches."""
    
    mock_response = AsyncMock()
    mock_response.text = NOT_FOUND_HTML
    
    async def mock_fetch(*args, **kwargs):
        return mock_response
    
    monkeypatch.setattr("civic_stack.djpb.scraper.fetch_with_retry", mock_fetch)
    
    results = await search("nonexistent")
    
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0].found is False
    assert results[0].status == RecordStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_fetch_found(monkeypatch):
    """Test fetch returns report when found via search."""
    
    mock_response = AsyncMock()
    mock_response.text = FOUND_HTML
    
    async def mock_fetch(*args, **kwargs):
        return mock_response
    
    monkeypatch.setattr("civic_stack.djpb.scraper.fetch_with_retry", mock_fetch)
    
    resp = await fetch("2025")
    
    assert isinstance(resp, CivicStackResponse)
    assert resp.found is True
    assert resp.module == "djpb"
    assert resp.status == RecordStatus.ACTIVE
    assert resp.result is not None


@pytest.mark.asyncio
async def test_fetch_not_found(monkeypatch):
    """Test fetch returns NOT_FOUND when report doesn't exist."""
    
    mock_response = AsyncMock()
    mock_response.text = NOT_FOUND_HTML
    
    async def mock_fetch(*args, **kwargs):
        return mock_response
    
    monkeypatch.setattr("civic_stack.djpb.scraper.fetch_with_retry", mock_fetch)
    
    resp = await fetch("Nonexistent Report 1999")
    
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
    
    monkeypatch.setattr("civic_stack.djpb.scraper.fetch_with_retry", mock_fetch)
    
    resp = await fetch("2025")
    
    data = resp.model_dump(mode="json")
    assert isinstance(data["fetched_at"], str)
    assert data["module"] == "djpb"
    assert data["status"] in [s.value for s in RecordStatus]
