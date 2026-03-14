"""FastAPI router for the LPSE module."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from civic_stack.shared.schema import CivicStackResponse

from .scraper import fetch, search, search_tenders

router = APIRouter(prefix="/lpse", tags=["LPSE"])


@router.get(
    "/vendor/{query}",
    response_model=CivicStackResponse,
    summary="Look up a vendor/company by name or NPWP",
)
async def get_vendor(query: str) -> CivicStackResponse:
    resp = await fetch(query)
    if not resp.found:
        raise HTTPException(status_code=404, detail=f"Vendor '{query}' not found in LPSE portals")
    return resp


@router.get(
    "/search",
    response_model=list[CivicStackResponse],
    summary="Search vendors across all LPSE portals",
)
async def search_vendors(q: str = Query(..., min_length=2)) -> list[CivicStackResponse]:
    return await search(q)


@router.get(
    "/tenders",
    response_model=list[CivicStackResponse],
    summary="Search active tenders by keyword",
)
async def search_tenders_route(q: str = Query(..., min_length=2)) -> list[CivicStackResponse]:
    return await search_tenders(q)
