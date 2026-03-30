"""
Unified MCP server for indonesia-civic-stack.

Registers all 40 tools from all 11 modules in a single MCP server.
This is the recommended way to use civic-stack with Claude Code.

Usage (stdio, for Claude Code / claude mcp add):
    python server.py

Usage (HTTP, for remote agents):
    python server.py --transport http
"""

from __future__ import annotations

import argparse
import logging

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="indonesia-civic-stack",
    instructions=(
        "Unified MCP server for indonesia-civic-stack — query 11 Indonesian government "
        "data portals. All tools return a CivicStackResponse envelope with fields: "
        "found (bool), status (ACTIVE|EXPIRED|SUSPENDED|REVOKED|NOT_FOUND|ERROR), "
        "result (dict), module (str), source_url (str). "
        "Check `found` and `status` before reading `result`. "
        "Set PROXY_URL env var if running outside Indonesia."
    ),
)


# Health endpoint for Railway/load balancers
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    from starlette.responses import JSONResponse

    return JSONResponse({"status": "ok", "server": "indonesia-civic-stack", "tools": 40})


# --- BPOM (Food & Drug) ---


@mcp.tool()
async def check_bpom(registration_no: str) -> dict:
    """
    Look up a BPOM product by registration number (e.g. 'MD 123456789').
    Returns product name, manufacturer, registration status, and expiry date.
    """
    from civic_stack.bpom.scraper import fetch

    r = await fetch(registration_no)
    return r.model_dump(mode="json")


@mcp.tool()
async def search_bpom(keyword: str) -> list[dict]:
    """
    Search BPOM product registry by keyword (product name, brand, manufacturer).
    Returns list of matching products with registration numbers and status.
    """
    from civic_stack.bpom.scraper import search

    results = await search(keyword)
    return [r.model_dump(mode="json") for r in results]


@mcp.tool()
async def get_bpom_status(registration_no: str) -> dict:
    """Quick status check for a BPOM registration number. Returns found + status only."""
    from civic_stack.bpom.scraper import fetch

    r = await fetch(registration_no)
    return {"found": r.found, "status": r.status, "module": r.module}


# --- BPJPH (Halal Certification) ---


@mcp.tool()
async def check_halal_cert(certificate_no: str) -> dict:
    """
    Look up a halal certificate by number from BPJPH (sertifikasi.halal.go.id).
    Returns company, product scope, expiry, and issuing body.
    """
    from civic_stack.bpjph.scraper import fetch

    r = await fetch(certificate_no)
    return r.model_dump(mode="json")


@mcp.tool()
async def lookup_halal_by_product(product_name: str) -> list[dict]:
    """Search halal certifications by product or company name."""
    from civic_stack.bpjph.scraper import search

    results = await search(product_name)
    return [r.model_dump(mode="json") for r in results]


@mcp.tool()
async def get_halal_status(certificate_no: str) -> dict:
    """Quick status check for a halal certificate number."""
    from civic_stack.bpjph.scraper import fetch

    r = await fetch(certificate_no)
    return {"found": r.found, "status": r.status, "module": r.module}


@mcp.tool()
async def cross_reference_halal_bpom(product_name: str) -> dict:
    """
    Cross-reference a product across both BPJPH (halal) and BPOM (food safety).
    Returns combined results from both registries for verification.
    """
    import asyncio

    from civic_stack.bpjph.scraper import search as bpjph_search
    from civic_stack.bpom.scraper import search as bpom_search

    halal, bpom = await asyncio.gather(
        bpjph_search(product_name),
        bpom_search(product_name),
    )
    return {
        "halal_results": [r.model_dump(mode="json") for r in halal],
        "bpom_results": [r.model_dump(mode="json") for r in bpom],
    }


# --- AHU (Company Registry) ---


@mcp.tool()
async def lookup_company_ahu(company_name: str) -> dict:
    """
    Look up a company in the AHU registry (ahu.go.id).
    Returns company type (PT/CV/Yayasan), registration date, status, address.
    """
    from civic_stack.ahu.scraper import fetch

    r = await fetch(company_name)
    return r.model_dump(mode="json")


@mcp.tool()
async def get_company_directors(company_name: str) -> dict:
    """Get directors and shareholders of a registered company from AHU."""
    from civic_stack.ahu.scraper import fetch

    r = await fetch(company_name)
    return r.model_dump(mode="json")


@mcp.tool()
async def verify_company_status(company_name: str) -> dict:
    """Quick check if a company is actively registered in AHU."""
    from civic_stack.ahu.scraper import fetch

    r = await fetch(company_name)
    return {"found": r.found, "status": r.status, "module": r.module}


@mcp.tool()
async def search_companies_ahu(keyword: str) -> list[dict]:
    """Search AHU company registry by keyword. Returns matching companies."""
    from civic_stack.ahu.scraper import search

    results = await search(keyword)
    return [r.model_dump(mode="json") for r in results]


# --- OJK (Financial Services Authority) ---


@mcp.tool()
async def check_ojk_license(institution_name: str) -> dict:
    """
    Check if a financial institution is licensed by OJK (api.ojk.go.id).
    Returns license type, status, and registration details.
    """
    from civic_stack.ojk.scraper import fetch

    r = await fetch(institution_name)
    return r.model_dump(mode="json")


@mcp.tool()
async def search_ojk_institutions(keyword: str) -> list[dict]:
    """Search OJK-licensed financial institutions by name or keyword."""
    from civic_stack.ojk.scraper import search

    results = await search(keyword)
    return [r.model_dump(mode="json") for r in results]


@mcp.tool()
async def get_ojk_status(institution_name: str) -> dict:
    """Quick OJK license status check."""
    from civic_stack.ojk.scraper import fetch

    r = await fetch(institution_name)
    return {"found": r.found, "status": r.status, "module": r.module}


@mcp.tool()
async def check_ojk_waspada(name: str) -> dict:
    """
    Check OJK's 'waspada' (alert/warning) list for illegal financial entities.
    If found, this entity is flagged by OJK as potentially fraudulent.
    """
    from civic_stack.ojk.scraper import fetch

    r = await fetch(name)
    return r.model_dump(mode="json")


# --- OSS NIB (Business Identity Number) ---


@mcp.tool()
async def lookup_nib(nib_number: str) -> dict:
    """Look up a business by NIB (Nomor Induk Berusaha) on OSS."""
    from civic_stack.oss_nib.scraper import fetch

    r = await fetch(nib_number)
    return r.model_dump(mode="json")


@mcp.tool()
async def verify_nib(nib_number: str) -> dict:
    """Quick verification of a NIB number."""
    from civic_stack.oss_nib.scraper import fetch

    r = await fetch(nib_number)
    return {"found": r.found, "status": r.status, "module": r.module}


@mcp.tool()
async def search_oss_businesses(keyword: str) -> list[dict]:
    """Search OSS business registry by company name or keyword."""
    from civic_stack.oss_nib.scraper import search

    results = await search(keyword)
    return [r.model_dump(mode="json") for r in results]


# --- LPSE (Government Procurement) ---


@mcp.tool()
async def lookup_vendor_lpse(vendor_name: str) -> dict:
    """Look up a vendor on LPSE government procurement portals."""
    from civic_stack.lpse.scraper import fetch

    r = await fetch(vendor_name)
    return r.model_dump(mode="json")


@mcp.tool()
async def search_lpse_vendors(keyword: str) -> list[dict]:
    """Search LPSE for vendors by name."""
    from civic_stack.lpse.scraper import search

    results = await search(keyword)
    return [r.model_dump(mode="json") for r in results]


@mcp.tool()
async def search_lpse_tenders(keyword: str) -> list[dict]:
    """Search LPSE for government procurement tenders by keyword."""
    from civic_stack.lpse.scraper import search

    results = await search(keyword)
    return [r.model_dump(mode="json") for r in results]


@mcp.tool()
async def get_lpse_portals() -> dict:
    """List available LPSE portals (ministry-level procurement sites)."""
    from civic_stack.lpse.scraper import fetch

    r = await fetch("__portals__")
    return r.model_dump(mode="json")


# --- KPU (Elections) ---


@mcp.tool()
async def get_candidate(candidate_id: str) -> dict:
    """Get detailed info about an election candidate from KPU (infopemilu.kpu.go.id)."""
    from civic_stack.kpu.scraper import fetch

    r = await fetch(candidate_id)
    return r.model_dump(mode="json")


@mcp.tool()
async def search_kpu_candidates(keyword: str) -> list[dict]:
    """Search KPU election candidates by name or region."""
    from civic_stack.kpu.scraper import search

    results = await search(keyword)
    return [r.model_dump(mode="json") for r in results]


@mcp.tool()
async def get_election_results_kpu(region_code: str) -> dict:
    """Get election results for a region from KPU Sirekap."""
    from civic_stack.kpu.scraper import fetch

    r = await fetch(region_code)
    return r.model_dump(mode="json")


@mcp.tool()
async def get_campaign_finance_kpu(candidate_id: str) -> dict:
    """Get campaign finance data for a candidate from KPU SILON."""
    from civic_stack.kpu.scraper import fetch

    r = await fetch(candidate_id)
    return r.model_dump(mode="json")


# --- LHKPN (Wealth Declarations) ---


# --- LHKPN (DEPRECATED) ---
# lhkpn tools removed in v1.0.0 — elhkpn.kpk.go.id is behind reCAPTCHA + login wall.
# Module code kept in civic_stack/lhkpn/ for reference.


# --- BPS (Statistics) ---


@mcp.tool()
async def search_bps_datasets(keyword: str) -> list[dict]:
    """
    Search BPS (Badan Pusat Statistik) datasets by keyword.
    Requires BPS_API_KEY env var (free registration at webapi.bps.go.id).
    """
    from civic_stack.bps.scraper import search

    results = await search(keyword)
    return [r.model_dump(mode="json") for r in results]


@mcp.tool()
async def get_bps_indicator(indicator_id: str, region_code: str = "0000") -> dict:
    """
    Get time-series data for a BPS statistical indicator.
    region_code '0000' = national. Requires BPS_API_KEY.
    """
    from civic_stack.bps.scraper import get_indicator

    r = await get_indicator(indicator_id, region_code=region_code)
    return r.model_dump(mode="json")


@mcp.tool()
async def list_bps_regions() -> dict:
    """List BPS region codes (provinces, kabupaten/kota)."""
    from civic_stack.bps.scraper import list_regions

    r = await list_regions()
    return r.model_dump(mode="json")


# --- BMKG (Weather & Earthquakes) ---


@mcp.tool()
async def get_bmkg_alerts() -> dict:
    """Get current BMKG weather alerts and significant weather warnings."""
    from civic_stack.bmkg.scraper import get_alerts

    r = await get_alerts()
    return r.model_dump(mode="json")


@mcp.tool()
async def get_weather_forecast(province: str = "DKIJakarta") -> dict:
    """
    Get BMKG weather forecast for an Indonesian province.
    Province names: DKIJakarta, JawaBarat, JawaTimur, Bali, etc. (no spaces).
    """
    from civic_stack.bmkg.scraper import get_forecast

    r = await get_forecast(province)
    return r.model_dump(mode="json")


@mcp.tool()
async def get_earthquake_history() -> list[dict]:
    """Get the last 15 significant earthquakes in Indonesia from BMKG."""
    from civic_stack.bmkg.scraper import search

    results = await search("gempa")
    return [r.model_dump(mode="json") for r in results] if isinstance(results, list) else results


@mcp.tool()
async def get_latest_earthquake() -> dict:
    """Get the most recent earthquake detected by BMKG. Returns magnitude, location, depth, time."""
    from civic_stack.bmkg.scraper import get_latest_earthquake as _get

    r = await _get()
    return r if isinstance(r, dict) else r.model_dump(mode="json")


# --- SIMBG (Building Permits) ---


@mcp.tool()
async def lookup_building_permit(permit_id: str) -> dict:
    """Look up a building permit (PBG) by ID on SIMBG (simbg.pu.go.id)."""
    from civic_stack.simbg.scraper import fetch

    r = await fetch(permit_id)
    return r.model_dump(mode="json")


@mcp.tool()
async def search_permits_by_area(keyword: str) -> list[dict]:
    """Search building permits by area, project name, or applicant."""
    from civic_stack.simbg.scraper import search

    results = await search(keyword)
    return [r.model_dump(mode="json") for r in results]


@mcp.tool()
async def list_simbg_portals() -> dict:
    """List available SIMBG regional portals."""
    from civic_stack.simbg.scraper import fetch

    r = await fetch("__portals__")
    return r.model_dump(mode="json")


# --- Entry point ---


def create_mcp_server() -> FastMCP:
    """Return the configured MCP server instance."""
    return mcp


def main():
    import os

    parser = argparse.ArgumentParser(description="indonesia-civic-stack unified MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode (default: stdio for Claude Code)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "0.0.0.0"),
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8000")),
        help="Port to bind to (default: 8000, or PORT env var)",
    )
    args = parser.parse_args()

    logger.info("Starting unified civic-stack MCP server (%d tools)", 40)
    mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
