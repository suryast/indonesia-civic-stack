"""OSS-NIB FastAPI router — mounts at /oss-nib."""

from __future__ import annotations

from fastapi import APIRouter, Query

from modules.oss_nib.scraper import fetch, search
from shared.schema import CivicStackResponse

router = APIRouter(prefix="/oss-nib", tags=["oss-nib"])


@router.get("/nib/{query:path}", response_model=CivicStackResponse,
            summary="Look up a business by NIB number or company name")
async def lookup_nib(
    query: str,
    debug: bool = Query(False),
    proxy_url: str | None = Query(None),
) -> CivicStackResponse:
    """Fetch an OSS-NIB business record by NIB number (13-digit) or company name."""
    return await fetch(query, debug=debug, proxy_url=proxy_url)


@router.get("/search", response_model=list[CivicStackResponse],
            summary="Search OSS businesses by name")
async def search_nib(
    q: str = Query(..., description="Company name keyword"),
    proxy_url: str | None = Query(None),
) -> list[CivicStackResponse]:
    """Search OSS-RBA by company name. Returns up to 10 results."""
    return await search(q, proxy_url=proxy_url)


@router.get("/verify/{nib_number}", response_model=CivicStackResponse,
            summary="Verify a NIB number status")
async def verify_nib(
    nib_number: str,
    proxy_url: str | None = Query(None),
) -> CivicStackResponse:
    """Verify a 13-digit NIB number and return its basic status."""
    resp = await fetch(nib_number, proxy_url=proxy_url)
    if resp.result:
        resp = resp.model_copy(update={"result": {
            k: resp.result[k]
            for k in ("nib", "company_name", "risk_level", "license_status", "domicile")
            if k in resp.result
        }})
    return resp
