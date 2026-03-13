"""BPJPH FastAPI router — mounts at /bpjph."""

from __future__ import annotations

from fastapi import APIRouter, Query

from modules.bpjph.scraper import cross_ref_bpom, fetch, search
from shared.schema import CivicStackResponse

router = APIRouter(prefix="/bpjph", tags=["bpjph"])


@router.get(
    "/check/{cert_no:path}",
    response_model=CivicStackResponse,
    summary="Look up a halal certificate by certificate number",
)
async def check_halal_cert(
    cert_no: str,
    debug: bool = Query(False),
    proxy_url: str | None = Query(None),
) -> CivicStackResponse:
    """Fetch a single BPJPH halal certificate record by certificate number."""
    return await fetch(cert_no, debug=debug, proxy_url=proxy_url)


@router.get(
    "/search",
    response_model=list[CivicStackResponse],
    summary="Search halal certificates by product or company name",
)
async def lookup_halal_by_product(
    q: str = Query(..., description="Product name or company name"),
    proxy_url: str | None = Query(None),
) -> list[CivicStackResponse]:
    """Search SiHalal by product name or company name."""
    return await search(q, proxy_url=proxy_url)


@router.get(
    "/status/{cert_no:path}",
    response_model=CivicStackResponse,
    summary="Get halal certificate status",
)
async def get_halal_status(
    cert_no: str,
    proxy_url: str | None = Query(None),
) -> CivicStackResponse:
    """Return status and expiry of a halal certificate."""
    resp = await fetch(cert_no, proxy_url=proxy_url)
    if resp.result:
        resp = resp.model_copy(
            update={
                "result": {
                    k: resp.result[k]
                    for k in ("cert_no", "company", "status", "expiry_date")
                    if k in resp.result
                }
            }
        )
    return resp


@router.get(
    "/cross-ref",
    summary="Cross-reference product between BPJPH (halal) and BPOM (registration)",
)
async def cross_reference(
    product_name: str = Query(..., description="Product name to cross-reference"),
    proxy_url: str | None = Query(None),
) -> dict:
    """
    Look up a product in both BPJPH (halal cert) and BPOM (product registration)
    and flag any status mismatch (e.g. BPOM active but halal cert expired).
    """
    return await cross_ref_bpom(product_name, proxy_url=proxy_url)
