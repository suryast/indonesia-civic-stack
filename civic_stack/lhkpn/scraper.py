"""
LHKPN scraper — KPK wealth declarations (Laporan Harta Kekayaan Penyelenggara Negara).

Source: elhkpn.kpk.go.id
Method: Playwright browser for reCAPTCHA v3 solving + HTML table parsing;
        pdfplumber for PDF extraction; Claude Vision API fallback for scanned PDFs.
Auth:   Public e-Announcement search — requires reCAPTCHA v3 token (solved via Playwright).

Dependency notes:
  - playwright is REQUIRED for search (pip install playwright && playwright install chromium)
  - pdfplumber + anthropic are OPTIONAL (extras: pip install indonesia-civic-stack[pdf])
"""

from __future__ import annotations

import asyncio
import logging
import re
from io import BytesIO
from typing import Any

import httpx

from civic_stack.shared.http import RateLimiter, civic_client
from civic_stack.shared.schema import (
    CivicStackResponse,
    RecordStatus,
    error_response,
    not_found_response,
)

from .normalizer import normalize_declaration, normalize_search_result

logger = logging.getLogger(__name__)

_BASE = "https://elhkpn.kpk.go.id"
_LOGIN_URL = _BASE + "/portal/user/login#announ"
_SEARCH_URL = _BASE + "/portal/user/check_search_announ"
_DETAIL_URL = _BASE + "/portal/user/detail_laporan_harta"
_PDF_URL = _BASE + "/portal/user/preview_laporan_pdf"
_RECAPTCHA_SITE_KEY = "6LfANPQrAAAAAFAKhYMdri6OAuMOPZZorjsCqUGk"

MODULE = "lhkpn"
SOURCE_URL = _BASE + "/portal/user/login#announ"

_limiter = RateLimiter(rate=0.25)


# ---------------------------------------------------------------------------
# Playwright-based reCAPTCHA v3 solver + search
# ---------------------------------------------------------------------------

async def _playwright_search(
    name: str,
    year: str = "",
    institution: str = "",
) -> list[dict[str, Any]]:
    """
    Use Playwright to load the LHKPN portal, solve reCAPTCHA v3, submit
    the announcement search form, and parse the results table.
    
    Table columns (14 cells per row, some hidden):
      [0] hidden hash, [1] hidden ID, [2] hidden, [3] hidden year,
      [4] hidden flag, [5] No., [6] Nama, [7] Lembaga, [8] Unit Kerja,
      [9] Jabatan, [10] Tanggal Lapor, [11] Jenis Laporan,
      [12] Total Harta Kekayaan, [13] Aksi (buttons)
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise ImportError(
            "playwright is required for LHKPN search. "
            "Install with: pip install playwright && playwright install chromium"
        ) from exc

    results: list[dict[str, Any]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        try:
            await page.goto(
                _LOGIN_URL, wait_until="domcontentloaded", timeout=30000,
            )
            await page.wait_for_function(
                "typeof grecaptcha !== 'undefined' && typeof grecaptcha.execute === 'function'",
                timeout=15000,
            )

            # Fill form
            await page.fill("#CARI_NAMA", name)
            if year:
                await page.fill("#CARI_TAHUN", year)
            if institution:
                await page.fill("#CARI_LEMBAGA", institution)

            # Solve reCAPTCHA v3
            token = await page.evaluate(
                f"""
                () => new Promise((resolve, reject) => {{
                    grecaptcha.execute('{_RECAPTCHA_SITE_KEY}', {{action: 'announcement'}})
                        .then(token => resolve(token))
                        .catch(err => reject(err.toString()));
                }})
                """
            )
            logger.debug("reCAPTCHA v3 token obtained (%d chars)", len(token))

            # Set token and submit (form.submit() causes navigation, returns result page)
            await page.evaluate(
                f'document.getElementById("g-recaptcha-response-announ").value = "{token}"'
            )
            async with page.expect_navigation(timeout=20000):
                await page.evaluate('document.getElementById("ajaxFormCari").submit()')

            await asyncio.sleep(2)

            # Parse result table rows
            rows = await page.query_selector_all("table tbody tr")
            for row in rows:
                cells = await row.query_selector_all("td")
                if len(cells) < 13:
                    continue
                texts = [await c.inner_text() for c in cells]
                texts = [t.strip() for t in texts]

                # Skip "Belum ada data" rows
                if any("belum ada" in t.lower() for t in texts):
                    continue

                results.append({
                    "report_hash": texts[0],
                    "report_id": texts[1],
                    "year": texts[3],
                    "no": texts[5].rstrip("."),
                    "nama": texts[6],
                    "lembaga": texts[7],
                    "unit_kerja": texts[8],
                    "jabatan": texts[9],
                    "tanggal_lapor": texts[10],
                    "jenis_laporan": texts[11],
                    "total_harta": texts[12],
                })

            # Extract download button IDs (base64 encoded report refs)
            download_btns = await page.query_selector_all(".yesdownl[data-id]")
            for i, btn in enumerate(download_btns):
                data_id = await btn.get_attribute("data-id")
                if data_id and i < len(results):
                    results[i]["download_id"] = data_id

        except Exception as exc:
            logger.error("Playwright LHKPN search failed: %s", exc)
        finally:
            await browser.close()

    return results


def _parse_rupiah(text: str) -> int:
    """Parse 'Rp.483.160.334' → 483160334"""
    cleaned = re.sub(r"[^0-9]", "", text)
    return int(cleaned) if cleaned else 0


# ---------------------------------------------------------------------------
# Internal helpers (httpx-based, for detail/PDF)
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
    try:
        import pdfplumber
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
    try:
        import anthropic
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
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    return json.loads(raw_text)


def extract_pdf(pdf_bytes: bytes) -> dict[str, Any]:
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
    try:
        results = await _playwright_search(name=query)
    except ImportError:
        return error_response(
            module=MODULE,
            query=query,
            source_url=SOURCE_URL,
            message="playwright not installed — required for LHKPN reCAPTCHA",
        )
    except Exception as exc:
        return error_response(
            module=MODULE,
            query=query,
            source_url=SOURCE_URL,
            message=f"LHKPN search failed: {exc}",
        )

    if not results:
        return not_found_response(module=MODULE, query=query, source_url=SOURCE_URL)

    best = results[0]

    normalized = {
        "official_name": best.get("nama", ""),
        "position": best.get("jabatan", ""),
        "ministry": best.get("lembaga", ""),
        "unit_kerja": best.get("unit_kerja", ""),
        "declaration_date": best.get("tanggal_lapor", ""),
        "declaration_type": best.get("jenis_laporan", ""),
        "declaration_year": best.get("year", ""),
        "total_assets_idr": _parse_rupiah(best.get("total_harta", "0")),
        "report_id": best.get("report_id", ""),
        "download_id": best.get("download_id", ""),
    }

    return CivicStackResponse(
        result=normalized,
        found=True,
        status=RecordStatus.ACTIVE,
        confidence=0.9,
        source_url=SOURCE_URL,
        fetched_at=__import__("datetime").datetime.utcnow(),
        module=MODULE,
        raw={"table_row": best, "all_results_count": len(results)},
    )


async def search(keyword: str, *, proxy_url: str | None = None) -> list[CivicStackResponse]:
    """Search officials by name, ministry, or position."""
    try:
        results = await _playwright_search(name=keyword)
    except (ImportError, Exception) as exc:
        logger.error("LHKPN search failed: %s", exc)
        return []

    responses: list[CivicStackResponse] = []
    for item in results[:20]:
        rec = {
            "official_name": item.get("nama", ""),
            "position": item.get("jabatan", ""),
            "ministry": item.get("lembaga", ""),
            "unit_kerja": item.get("unit_kerja", ""),
            "declaration_date": item.get("tanggal_lapor", ""),
            "declaration_type": item.get("jenis_laporan", ""),
            "declaration_year": item.get("year", ""),
            "total_assets_idr": _parse_rupiah(item.get("total_harta", "0")),
            "report_id": item.get("report_id", ""),
            "download_id": item.get("download_id", ""),
        }
        responses.append(
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
    return responses


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
