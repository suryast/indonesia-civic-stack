"""AHU FastAPI router — mounts at /ahu."""

from __future__ import annotations

from fastapi import APIRouter, Query

from modules.ahu.scraper import fetch, search
from shared.schema import CivicStackResponse

router = APIRouter(prefix="/ahu", tags=["ahu"])


@router.get(
    "/company/{query:path}",
    response_model=CivicStackResponse,
    summary="Look up a company in the AHU registry",
)
async def lookup_company_ahu(
    query: str,
    debug: bool = Query(False),
    proxy_url: str | None = Query(None, description="Cloudflare Worker or residential proxy URL"),
) -> CivicStackResponse:
    """
    Fetch a company record from ahu.go.id by name or registration number.

    **Note:** AHU blocks datacenter IPs. Provide `proxy_url` in production.
    """
    return await fetch(query, debug=debug, proxy_url=proxy_url)


@router.get(
    "/company/{company_id}/directors",
    response_model=CivicStackResponse,
    summary="Get directors and commissioners for a company",
)
async def get_company_directors(
    company_id: str,
    proxy_url: str | None = Query(None),
) -> CivicStackResponse:
    """Fetch company detail and return with directors/commissioners in result."""
    resp = await fetch(company_id, proxy_url=proxy_url)
    if resp.result:
        resp = resp.model_copy(
            update={
                "result": {
                    k: resp.result[k]
                    for k in (
                        "company_name",
                        "registration_no",
                        "directors",
                        "commissioners",
                        "legal_status",
                    )
                    if k in resp.result
                }
            }
        )
    return resp


@router.get(
    "/company/{company_id}/status",
    response_model=CivicStackResponse,
    summary="Verify company legal status",
)
async def verify_company_status(
    company_id: str,
    proxy_url: str | None = Query(None),
) -> CivicStackResponse:
    """Return legal status, registration number, and deed date for a company."""
    resp = await fetch(company_id, proxy_url=proxy_url)
    if resp.result:
        resp = resp.model_copy(
            update={
                "result": {
                    k: resp.result[k]
                    for k in (
                        "company_name",
                        "registration_no",
                        "legal_status",
                        "legal_form",
                        "deed_date",
                        "domicile",
                    )
                    if k in resp.result
                }
            }
        )
    return resp


@router.get(
    "/search",
    response_model=list[CivicStackResponse],
    summary="Search AHU company registry by keyword",
)
async def search_companies(
    q: str = Query(..., description="Company name keyword"),
    proxy_url: str | None = Query(None),
) -> list[CivicStackResponse]:
    """Search the AHU registry by company name keyword. Returns up to 10 results."""
    return await search(q, proxy_url=proxy_url)
