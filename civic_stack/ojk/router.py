"""OJK FastAPI router — mounts at /ojk."""

from __future__ import annotations

from fastapi import APIRouter, Query

from civic_stack.ojk.scraper import check_waspada, fetch, search
from civic_stack.shared.schema import CivicStackResponse

router = APIRouter(prefix="/ojk", tags=["ojk"])


@router.get(
    "/check/{name_or_id:path}",
    response_model=CivicStackResponse,
    summary="Look up an OJK licensed institution",
)
async def check_ojk_license(
    name_or_id: str,
    debug: bool = Query(False),
    proxy_url: str | None = Query(None),
) -> CivicStackResponse:
    """Fetch a single OJK institution record by name or license number."""
    return await fetch(name_or_id, debug=debug, proxy_url=proxy_url)


@router.get(
    "/search", response_model=list[CivicStackResponse], summary="Search OJK licensed institutions"
)
async def search_ojk_institutions(
    q: str = Query(..., description="Institution name or keyword"),
    institution_type: str | None = Query(
        None,
        description="bank_umum|bpr|fintech_p2p|fintech_payment|asuransi|dana_pensiun|manajer_investasi|sekuritas",
    ),
    status: str | None = Query(None, description="aktif|dicabut|dibekukan"),
    proxy_url: str | None = Query(None),
) -> list[CivicStackResponse]:
    """Search OJK registry by keyword with optional type and status filters."""
    filters: dict = {}
    if institution_type:
        filters["institution_type"] = institution_type
    if status:
        filters["status"] = status
    return await search(q, filters=filters or None, proxy_url=proxy_url)


@router.get(
    "/status/{name_or_id:path}", response_model=CivicStackResponse, summary="Get OJK license status"
)
async def get_ojk_status(
    name_or_id: str,
    proxy_url: str | None = Query(None),
) -> CivicStackResponse:
    """Return license status only (lighter than /check)."""
    resp = await fetch(name_or_id, proxy_url=proxy_url)
    if resp.result:
        resp = resp.model_copy(
            update={
                "result": {
                    k: resp.result[k]
                    for k in (
                        "institution_name",
                        "license_no",
                        "institution_type",
                        "license_status",
                    )
                    if k in resp.result
                }
            }
        )
    return resp


@router.get(
    "/waspada", response_model=CivicStackResponse, summary="Check OJK Waspada Investasi alert list"
)
async def waspada_check(
    q: str = Query(..., description="Entity name to check against investment alert list"),
    proxy_url: str | None = Query(None),
) -> CivicStackResponse:
    """
    Check if an entity is on OJK's Waspada Investasi list
    (unlicensed / potentially fraudulent investment entities).
    Returns NOT_FOUND if the entity is clean.
    """
    return await check_waspada(q, proxy_url=proxy_url)
