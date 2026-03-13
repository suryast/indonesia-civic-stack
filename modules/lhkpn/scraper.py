"""
LHKPN scraper — KPK wealth declarations (Laporan Harta Kekayaan Penyelenggara Negara).

Source: elhkpn.kpk.go.id
Method: REST API for search + official listing; pdfplumber for PDF extraction;
        Claude Vision API fallback for scanned/image-based PDFs.
Auth:   Public search tier — no login required.

Dependency notes:
  - pdfplumber + anthropic are OPTIONAL (extras: pip install indonesia-civic-stack[pdf])
  - If unavailable, PDF-based methods raise ImportError with install instructions.
"""

from __future__ import annotations

import logging
from io import BytesIO
from typing import Any

import httpx

from shared.http import RateLimiter, civic_client
from shared.schema import CivicStackResponse, RecordStatus, error_response, not_found_response

from .normalizer import normalize_declaration, normalize_search_result

logger = logging.getLogger(__name__)

# elhkpn public API endpoints (no auth required for public tier)
_BASE = "https://elhkpn.kpk.go.id"
_SEARCH_URL = _BASE + "/portal/user/check_a_lhkpn"  # POST: {"nama": "..."}
_DETAIL_URL = _BASE + "/portal/user/detail_laporan_harta"  # POST: {"id_laporan": "..."}
_PDF_URL = _BASE + "/portal/user/preview_laporan_pdf"  # GET: ?id_laporan=...

MODULE = "lhkpn"
SOURCE_URL = _BASE + "/portal/user/check_a_lhkpn"

_limiter = RateLimiter(rate=0.25)  # 1 req / 4s — KPK portal is conservative


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _post_json(
    client: httpx.AsyncClient,
    url: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    try:
        await _limiter.acquire()
        resp = await client.post(url, json=payload, timeout=20.0)
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as exc:
        logger.warning("LHKPN request failed %s: %s", url, exc)
        return None


async def _download_pdf(client: httpx.AsyncClient, report_id: str) -> bytes | None:
    try:
        await _limiter.acquire()
        resp = await client.get(_PDF_URL, params={"id_laporan": report_id}, timeout=30.0)
        resp.raise_for_status()
        if "application/pdf" not in resp.headers.get("content-type", ""):
            logger.warning("Expected PDF but got %s", resp.headers.get("content-type"))
            return None
        return resp.content
    except Exception as exc:
        logger.warning("PDF download failed for report %s: %s", report_id, exc)
        return None


def _extract_pdf_pdfplumber(pdf_bytes: bytes) -> dict[str, Any]:
    """Extract structured data from a native/text-layer PDF using pdfplumber."""
    try:
        import pdfplumber  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "pdfplumber is required for PDF extraction. "
            "Install with: pip install 'indonesia-civic-stack[pdf]'"
        ) from exc

    extracted: dict[str, Any] = {"pages": [], "raw_text": ""}
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        full_text_parts: list[str] = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text_parts.append(text)
            tables = page.extract_tables() or []
            extracted["pages"].append({"text": text, "tables": tables})
        extracted["raw_text"] = "\n".join(full_text_parts)

    return extracted


def _extract_pdf_claude_vision(pdf_bytes: bytes) -> dict[str, Any]:
    """
    Fallback: use Claude Vision API to extract data from scanned/image PDFs.

    Requires the `anthropic` package and ANTHROPIC_API_KEY environment variable.
    """
    try:
        import anthropic  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "anthropic is required for Vision PDF extraction. "
            "Install with: pip install 'indonesia-civic-stack[pdf]'"
        ) from exc

    import base64
    import os

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise OSError("ANTHROPIC_API_KEY is not set — required for Vision PDF fallback")

    client = anthropic.Anthropic(api_key=api_key)
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode()

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extract the following fields from this LHKPN (Indonesian wealth "
                            "declaration) PDF. Return JSON only, no commentary:\n"
                            "{\n"
                            '  "official_name": "",\n'
                            '  "position": "",\n'
                            '  "ministry": "",\n'
                            '  "declaration_year": "",\n'
                            '  "submission_date": "",\n'
                            '  "total_assets_idr": 0,\n'
                            '  "total_liabilities_idr": 0,\n'
                            '  "net_assets_idr": 0,\n'
                            '  "asset_breakdown": {\n'
                            '    "immovable_property_idr": 0,\n'
                            '    "movable_property_idr": 0,\n'
                            '    "securities_idr": 0,\n'
                            '    "cash_idr": 0,\n'
                            '    "other_assets_idr": 0\n'
                            "  },\n"
                            '  "income_sources": []\n'
                            "}"
                        ),
                    },
                ],
            }
        ],
    )

    import json

    raw_text = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    return json.loads(raw_text)


def extract_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    """
    Extract LHKPN data from PDF bytes.

    Strategy:
      1. Try pdfplumber (fast, accurate for text-layer PDFs).
      2. If extracted text is empty or very short, fall back to Claude Vision API.
    """
    try:
        data = _extract_pdf_pdfplumber(pdf_bytes)
        if len(data.get("raw_text", "")) > 200:
            return data
        logger.info("pdfplumber yielded sparse text — falling back to Claude Vision")
    except (ImportError, Exception) as exc:
        logger.warning("pdfplumber extraction failed: %s — trying Vision", exc)

    return _extract_pdf_claude_vision(pdf_bytes)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def fetch(query: str, *, proxy_url: str | None = None) -> CivicStackResponse:
    """Look up a public official by name and return their latest LHKPN declaration."""
    async with civic_client(proxy_url=proxy_url) as client:
        search_data = await _post_json(client, _SEARCH_URL, {"nama": query})

    if not search_data:
        return error_response(
            module=MODULE,
            query=query,
            source_url=SOURCE_URL,
            message="LHKPN portal unreachable",
        )

    officials = search_data.get("data") or []
    if not officials:
        return not_found_response(module=MODULE, query=query, source_url=SOURCE_URL)

    best = officials[0]
    report_id = str(best.get("id_laporan") or best.get("id") or "")

    # Fetch detail
    detail_data: dict[str, Any] = {}
    if report_id:
        async with civic_client(proxy_url=proxy_url) as client:
            raw_detail = await _post_json(client, _DETAIL_URL, {"id_laporan": report_id})
        if raw_detail:
            detail_data = raw_detail.get("data") or {}

    normalized = normalize_declaration({**best, **detail_data}, query=query)
    return CivicStackResponse(
        result=normalized,
        found=True,
        status=RecordStatus.ACTIVE,
        confidence=normalized.pop("_confidence", 0.9),
        source_url=SOURCE_URL,
        fetched_at=__import__("datetime").datetime.utcnow(),
        module=MODULE,
        raw={"report_id": report_id},
    )


async def search(keyword: str, *, proxy_url: str | None = None) -> list[CivicStackResponse]:
    """Search officials by name, ministry, or position."""
    async with civic_client(proxy_url=proxy_url) as client:
        data = await _post_json(client, _SEARCH_URL, {"nama": keyword})

    if not data:
        return []

    results: list[CivicStackResponse] = []
    for item in (data.get("data") or [])[:20]:
        rec = normalize_search_result(item)
        results.append(
            CivicStackResponse(
                result=rec,
                found=True,
                status=RecordStatus.ACTIVE,
                confidence=0.8,
                source_url=SOURCE_URL,
                fetched_at=__import__("datetime").datetime.utcnow(),
                module=MODULE,
            )
        )
    return results


async def get_pdf(report_id: str, *, proxy_url: str | None = None) -> dict[str, Any]:
    """Download and extract a specific LHKPN PDF by report ID."""
    async with civic_client(proxy_url=proxy_url) as client:
        pdf_bytes = await _download_pdf(client, report_id)

    if not pdf_bytes:
        return {"error": "PDF download failed", "report_id": report_id}

    return extract_pdf(pdf_bytes)


async def compare_lhkpn(
    official_id: str,
    year_a: int,
    year_b: int,
    *,
    proxy_url: str | None = None,
) -> dict[str, Any]:
    """
    Compare two LHKPN declarations for the same official across different years.
    Returns delta for total assets, liabilities, and net worth.
    """
    async with civic_client(proxy_url=proxy_url) as client:
        data_a = await _post_json(client, _DETAIL_URL, {"id_laporan": f"{official_id}_{year_a}"})
        data_b = await _post_json(client, _DETAIL_URL, {"id_laporan": f"{official_id}_{year_b}"})

    if not data_a or not data_b:
        return {"error": "Could not retrieve one or both declarations"}

    rec_a = normalize_declaration(data_a.get("data") or {}, query="")
    rec_b = normalize_declaration(data_b.get("data") or {}, query="")

    def _delta(key: str) -> int | None:
        a = rec_a.get(key)
        b = rec_b.get(key)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return int(b - a)
        return None

    return {
        "official_id": official_id,
        "year_a": year_a,
        "year_b": year_b,
        "declaration_a": rec_a,
        "declaration_b": rec_b,
        "delta": {
            "total_assets_idr": _delta("total_assets_idr"),
            "total_liabilities_idr": _delta("total_liabilities_idr"),
            "net_assets_idr": _delta("net_assets_idr"),
        },
    }
