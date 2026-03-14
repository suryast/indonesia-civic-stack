"""FastAPI router for the BPS module."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from civic_stack.shared.schema import CivicStackResponse

from .scraper import fetch, get_indicator, list_regions, search

router = APIRouter(prefix="/bps", tags=["BPS"])


@router.get(
    "/dataset/{subject_id}",
    response_model=CivicStackResponse,
    summary="Fetch a BPS dataset by subject ID",
)
async def get_dataset(subject_id: str) -> CivicStackResponse:
    resp = await fetch(subject_id)
    if not resp.found:
        raise HTTPException(status_code=404, detail=f"BPS dataset '{subject_id}' not found")
    return resp


@router.get(
    "/search",
    response_model=list[CivicStackResponse],
    summary="Search BPS datasets by keyword",
)
async def search_datasets(q: str = Query(..., min_length=2)) -> list[CivicStackResponse]:
    return await search(q)


@router.get(
    "/indicator/{indicator_id}",
    response_model=CivicStackResponse,
    summary="Get time-series data for a BPS indicator",
)
async def get_indicator_data(
    indicator_id: str,
    region: str = Query("0000", description="BPS wilayah code (default: national)"),
    years: str | None = Query(None, description="Comma-separated years, e.g. 2020,2021,2022"),
) -> CivicStackResponse:
    resp = await get_indicator(indicator_id, region_code=region, year_range=years)
    if not resp.found:
        raise HTTPException(status_code=404, detail=f"Indicator '{indicator_id}' not found")
    return resp


@router.get(
    "/regions",
    summary="List BPS regional codes",
)
async def get_regions(parent: str = Query("0", description="Parent region code")) -> list[dict]:
    return await list_regions(parent)
