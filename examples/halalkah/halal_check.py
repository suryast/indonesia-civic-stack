"""
HalalKah integration — civic-stack data layer.

This module replaces the bespoke scraper previously embedded in halalkah.id.
Drop this in as the data layer; the halalkah.id application logic is unchanged.

Usage:
    from examples.halalkah.halal_check import HalalKahChecker

    checker = HalalKahChecker()
    result = await checker.verify_product("mie goreng spesial")
    result = await checker.verify_by_cert_no("ID00110019882120240001")
    result = await checker.verify_by_bpom_no("BPOM MD 123456789012")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from modules.bpjph import cross_ref_bpom
from modules.bpjph import fetch as bpjph_fetch
from modules.bpom import fetch as bpom_fetch

logger = logging.getLogger(__name__)


@dataclass
class HalalVerificationResult:
    """
    The result object halalkah.id application code works with.

    This is the same shape as the old bespoke scraper result — no
    changes needed in the halalkah.id frontend or business logic.
    """

    product_name: str
    is_halal: bool
    halal_status: str  # "CERTIFIED" | "EXPIRED" | "NOT_FOUND" | "ERROR"
    bpom_status: str  # "ACTIVE" | "EXPIRED" | "NOT_FOUND" | "ERROR"
    has_mismatch: bool  # True when halal/BPOM statuses diverge
    mismatch_detail: str | None

    cert_no: str | None
    cert_expiry: str | None
    cert_issuer: str | None  # "BPJPH" | "MUI"

    bpom_reg_no: str | None
    bpom_expiry: str | None
    company: str | None

    fetched_at: str
    confidence: float
    source_modules: list[str]

    # Raw civic-stack responses available for debugging / detailed UI
    _bpjph_raw: dict[str, Any] | None = None
    _bpom_raw: dict[str, Any] | None = None


class HalalKahChecker:
    """
    Halal verification checker backed by indonesia-civic-stack modules.

    Replaces the bespoke halalkah.id scraper. All methods are async
    and return HalalVerificationResult — the same shape the halalkah.id
    frontend already expects.
    """

    def __init__(self, proxy_url: str | None = None) -> None:
        """
        Args:
            proxy_url: Optional proxy for BPJPH/AHU (Cloudflare Worker or residential).
                       Not required for BPOM (static HTML, no IP blocking).
        """
        self.proxy_url = proxy_url

    async def verify_product(self, product_name: str) -> HalalVerificationResult:
        """
        Primary halalkah.id verification flow — by product name.

        Runs BPJPH (halal cert) and BPOM (registration) lookups in parallel,
        returns a combined result highlighting any status mismatch.
        """
        cross_ref = await cross_ref_bpom(product_name, proxy_url=self.proxy_url)
        return self._build_result(product_name, cross_ref)

    async def verify_by_cert_no(self, cert_no: str) -> HalalVerificationResult:
        """
        Verify by halal certificate number (e.g. from QR code scan).
        Also fetches matching BPOM registration for full verification.
        """
        resp = await bpjph_fetch(cert_no, proxy_url=self.proxy_url)
        product_name = ""
        if resp.result and resp.result.get("product_list"):
            product_name = resp.result["product_list"][0] if resp.result["product_list"] else ""

        cross_ref: dict[str, Any] = {
            "product_name": product_name,
            "bpjph": resp.model_dump(mode="json"),
            "bpom": None,
            "mismatch": False,
            "mismatch_detail": None,
        }

        # Enrich with BPOM data if we have a product name
        if product_name:
            from modules.bpom import search as bpom_search

            bpom_results = await bpom_search(product_name)
            if bpom_results and bpom_results[0].found:
                bpom_data = bpom_results[0].model_dump(mode="json")
                cross_ref["bpom"] = bpom_data
                bpjph_active = resp.status == "ACTIVE"
                bpom_active = bpom_results[0].status == "ACTIVE"
                if bpjph_active != bpom_active:
                    cross_ref["mismatch"] = True
                    cross_ref["mismatch_detail"] = (
                        f"Halal cert is {resp.status} but BPOM registration is {bpom_results[0].status}"
                    )

        return self._build_result(product_name or cert_no, cross_ref)

    async def verify_by_bpom_no(self, bpom_reg_no: str) -> HalalVerificationResult:
        """
        Verify by BPOM registration number — useful when scanning product packaging.
        Cross-references with halal certificate data.
        """
        bpom_resp = await bpom_fetch(bpom_reg_no)
        product_name = bpom_resp.result.get("product_name", "") if bpom_resp.result else ""

        cross_ref: dict[str, Any] = {
            "product_name": product_name,
            "bpjph": None,
            "bpom": bpom_resp.model_dump(mode="json"),
            "mismatch": False,
            "mismatch_detail": None,
        }

        if product_name:
            from modules.bpjph import search as bpjph_search

            bpjph_results = await bpjph_search(product_name, proxy_url=self.proxy_url)
            if bpjph_results and bpjph_results[0].found:
                bpjph_data = bpjph_results[0].model_dump(mode="json")
                cross_ref["bpjph"] = bpjph_data
                bpjph_active = bpjph_results[0].status == "ACTIVE"
                bpom_active = bpom_resp.status == "ACTIVE"
                if bpom_active and not bpjph_active:
                    cross_ref["mismatch"] = True
                    cross_ref["mismatch_detail"] = (
                        f"BPOM registration is {bpom_resp.status} "
                        f"but no active halal cert found (status: {bpjph_results[0].status})"
                    )

        return self._build_result(product_name or bpom_reg_no, cross_ref)

    # ── Private ───────────────────────────────────────────────────────────────

    def _build_result(
        self, product_name: str, cross_ref: dict[str, Any]
    ) -> HalalVerificationResult:
        bpjph = cross_ref.get("bpjph") or {}
        bpom = cross_ref.get("bpom") or {}

        bpjph_status = bpjph.get("status", "NOT_FOUND")
        bpom_status = bpom.get("status", "NOT_FOUND")

        is_halal = bpjph_status == "ACTIVE"
        halal_status = "CERTIFIED" if is_halal else bpjph_status

        bpjph_result = bpjph.get("result") or {}
        bpom_result = bpom.get("result") or {}

        return HalalVerificationResult(
            product_name=product_name,
            is_halal=is_halal,
            halal_status=halal_status,
            bpom_status=bpom_status,
            has_mismatch=cross_ref.get("mismatch", False),
            mismatch_detail=cross_ref.get("mismatch_detail"),
            cert_no=bpjph_result.get("cert_no"),
            cert_expiry=bpjph_result.get("expiry_date"),
            cert_issuer=bpjph_result.get("issuer"),
            bpom_reg_no=bpom_result.get("registration_no"),
            bpom_expiry=bpom_result.get("expiry_date"),
            company=bpjph_result.get("company") or bpom_result.get("company"),
            fetched_at=datetime.now(UTC).isoformat(),
            confidence=min(
                bpjph.get("confidence", 0.0) or 0.0,
                bpom.get("confidence", 0.0) or 0.0,
            )
            if (bpjph and bpom)
            else max(
                bpjph.get("confidence", 0.0) or 0.0,
                bpom.get("confidence", 0.0) or 0.0,
            ),
            source_modules=[m for m, d in [("bpjph", bpjph), ("bpom", bpom)] if d],
            _bpjph_raw=bpjph,
            _bpom_raw=bpom,
        )
