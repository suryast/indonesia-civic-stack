"""FastAPI router for the SIMBG module."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from shared.schema import CivicStackResponse

from .scraper import PILOT_PORTALS, fetch, search

router = APIRouter(prefix="/simbg", tags=["SIMBG"])


@router.get(
    "/permit/{query:path}",
    response_model=CivicStackResponse,
    summary="Look up building permit(s) by address, permit number, or property ID",
)
async def get_permit(query: str) -> CivicStackResponse:
    resp = await fetch(query)
    if not resp.found:
        raise HTTPException(status_code=404, detail=f"No building permit found for '{query}'")
    return resp


@router.get(
    "/search",
    response_model=list[CivicStackResponse],
    summary="Search building permits across SIMBG portals",
)
async def search_permits(q: str = Query(..., min_length=3)) -> list[CivicStackResponse]:
    return await search(q)


@router.get(
    "/portals",
    summary="List monitored SIMBG pilot portals",
)
async def list_portals() -> list[dict]:
    return PILOT_PORTALS
