"""
BPOM FastAPI router — mounts at /bpom.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from modules.bpom.scraper import fetch, search
from shared.schema import CivicStackResponse

router = APIRouter(prefix="/bpom", tags=["bpom"])


class CheckResponse(CivicStackResponse):
    pass


@router.get(
    "/check/{registration_no:path}",
    response_model=CivicStackResponse,
    summary="Look up a BPOM product by registration number",
)
async def check_bpom(
    registration_no: str,
    debug: bool = Query(False, description="Include raw scraped data in response"),
    proxy_url: str | None = Query(None, description="Optional proxy URL for IP rotation"),
) -> CivicStackResponse:
    """
    Fetch a single BPOM product registration record.

    - **registration_no**: e.g. `BPOM MD 123456789012` or `MD 123456789012`
    - **debug**: Set to `true` to include raw scraped HTML fields
    """
    return await fetch(registration_no, debug=debug, proxy_url=proxy_url)


@router.get(
    "/search",
    response_model=list[CivicStackResponse],
    summary="Search BPOM products by name or keyword",
)
async def search_bpom(
    q: str = Query(..., description="Product name or partial name to search"),
    proxy_url: str | None = Query(None, description="Optional proxy URL for IP rotation"),
) -> list[CivicStackResponse]:
    """
    Search the BPOM registry by product name. Returns up to 10 results.
    """
    return await search(q, proxy_url=proxy_url)


@router.get(
    "/status/{registration_no:path}",
    response_model=CivicStackResponse,
    summary="Get BPOM registration status (lighter than /check)",
)
async def get_bpom_status(
    registration_no: str,
    proxy_url: str | None = Query(None),
) -> CivicStackResponse:
    """
    Returns the status and expiry of a BPOM registration without full detail.
    Internally calls the same fetch() but clients can use this endpoint
    when they only need the status field.
    """
    resp = await fetch(registration_no, proxy_url=proxy_url)
    # Slim down the result to status-relevant fields only
    if resp.result:
        resp = resp.model_copy(
            update={
                "result": {
                    k: resp.result[k]
                    for k in (
                        "registration_no",
                        "registration_status",
                        "expiry_date",
                        "product_name",
                    )
                    if k in resp.result
                }
            }
        )
    return resp
