"""FastAPI router for the LHKPN module."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from shared.schema import CivicStackResponse

from .scraper import compare_lhkpn, fetch, search

router = APIRouter(prefix="/lhkpn", tags=["LHKPN"])


@router.get(
    "/official/{name:path}",
    response_model=CivicStackResponse,
    summary="Look up an official's latest LHKPN wealth declaration",
)
async def get_official(name: str) -> CivicStackResponse:
    resp = await fetch(name)
    if not resp.found:
        raise HTTPException(status_code=404, detail=f"No LHKPN found for '{name}'")
    return resp


@router.get(
    "/search",
    response_model=list[CivicStackResponse],
    summary="Search officials by name, ministry, or position",
)
async def search_officials(q: str = Query(..., min_length=2)) -> list[CivicStackResponse]:
    return await search(q)


@router.get(
    "/compare",
    summary="Compare wealth declarations across two years for an official",
)
async def compare(
    official_id: str,
    year_a: int,
    year_b: int,
) -> dict:
    result = await compare_lhkpn(official_id, year_a, year_b)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
