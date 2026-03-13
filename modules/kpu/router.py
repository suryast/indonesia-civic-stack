"""KPU FastAPI router — mounts at /kpu."""

from __future__ import annotations

from fastapi import APIRouter, Query

from modules.kpu.scraper import fetch, get_campaign_finance, get_election_results, search
from shared.schema import CivicStackResponse

router = APIRouter(prefix="/kpu", tags=["kpu"])


@router.get("/candidate/{candidate_id}", response_model=CivicStackResponse,
            summary="Get a KPU candidate profile")
async def get_candidate(
    candidate_id: str,
    debug: bool = Query(False),
) -> CivicStackResponse:
    """Fetch a candidate profile by KPU ID or name."""
    return await fetch(candidate_id, debug=debug)


@router.get("/search", response_model=list[CivicStackResponse],
            summary="Search KPU candidates by name")
async def search_candidates(
    q: str = Query(..., description="Candidate name"),
    election_type: str | None = Query(None, description="presiden|dpr|dpd|dprd_prov|dprd_kab"),
    region_code: str | None = Query(None),
    party: str | None = Query(None),
) -> list[CivicStackResponse]:
    """Search candidates by name with optional filters."""
    filters: dict = {}
    if election_type:
        filters["election_type"] = election_type
    if region_code:
        filters["region_code"] = region_code
    if party:
        filters["party"] = party
    return await search(q, filters=filters or None)


@router.get("/results/{region_code}", response_model=CivicStackResponse,
            summary="Get SIREKAP election results for a region")
async def election_results(
    region_code: str,
    election_type: str = Query("dpr", description="presiden|dpr|dpd|dprd_prov|dprd_kab"),
) -> CivicStackResponse:
    """Fetch real-time SIREKAP vote tallies. Use region_code='0' for national."""
    return await get_election_results(region_code, election_type)


@router.get("/finance/{candidate_id}", response_model=CivicStackResponse,
            summary="Get SILON campaign finance for a candidate")
async def campaign_finance(candidate_id: str) -> CivicStackResponse:
    """Fetch SILON campaign finance summary."""
    return await get_campaign_finance(candidate_id)
