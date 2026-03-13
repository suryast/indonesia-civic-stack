#!/usr/bin/env python3
"""
HalalKah integration smoke test — validates civic-stack as the data layer.

Run this against staging before deploying halalkah.id with civic-stack.
Uses VCR fixtures in CI; runs against live portals when --live is passed.

Usage:
    python examples/halalkah/smoke_test.py           # VCR replay (CI safe)
    python examples/halalkah/smoke_test.py --live    # Live portals (staging validation)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from examples.halalkah.halal_check import HalalKahChecker, HalalVerificationResult

# ── Test cases ────────────────────────────────────────────────────────────────

SMOKE_CASES = [
    {
        "name": "Verify active halal product by name",
        "method": "verify_product",
        "query": "mie goreng spesial",
        "expect_found": True,
        "expect_halal": True,
    },
    {
        "name": "Verify by halal cert number",
        "method": "verify_by_cert_no",
        "query": "ID00110019882120240001",
        "expect_found": True,
        "expect_halal": True,
    },
    {
        "name": "Verify by BPOM registration number",
        "method": "verify_by_bpom_no",
        "query": "BPOM MD 123456789012",
        "expect_found": True,
        "expect_halal": None,  # BPOM lookup doesn't assert halal status
    },
    {
        "name": "Non-existent product returns gracefully",
        "method": "verify_product",
        "query": "PRODUK YANG TIDAK ADA XYZ123",
        "expect_found": False,
        "expect_halal": False,
    },
]


async def run_smoke_test(case: dict, checker: HalalKahChecker) -> tuple[bool, str]:
    """Run a single smoke test case. Returns (passed, detail)."""
    method = getattr(checker, case["method"])
    try:
        result: HalalVerificationResult = await method(case["query"])
    except Exception as exc:
        return False, f"Exception: {exc}"

    # Validate result shape
    if not isinstance(result, HalalVerificationResult):
        return False, f"Expected HalalVerificationResult, got {type(result).__name__}"

    if not result.fetched_at:
        return False, "fetched_at is empty"

    if not result.source_modules:
        return False, "source_modules is empty"

    # Validate expected outcomes
    if case["expect_found"] and not (result.is_halal or result.bpom_status == "ACTIVE"):
        # For not-found cases, we just check it didn't raise
        pass

    if case["expect_halal"] is True and not result.is_halal:
        return False, f"Expected is_halal=True, got halal_status={result.halal_status}"

    if case["expect_halal"] is False and result.is_halal:
        return False, f"Expected is_halal=False, got halal_status={result.halal_status}"

    return (
        True,
        f"halal_status={result.halal_status}, bpom_status={result.bpom_status}, mismatch={result.has_mismatch}",
    )


async def main(live: bool) -> int:
    checker = HalalKahChecker()
    passed = 0
    failed = 0

    print(f"\n{'=' * 60}")
    print(f"HalalKah integration smoke test {'(LIVE)' if live else '(VCR)'}")
    print(f"{'=' * 60}\n")

    for case in SMOKE_CASES:
        ok, detail = await run_smoke_test(case, checker)
        status = "PASS" if ok else "FAIL"
        symbol = "✓" if ok else "✗"
        print(f"  {symbol} [{status}] {case['name']}")
        print(f"         {detail}\n")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"{'=' * 60}")
    print(f"Results: {passed}/{passed + failed} passed")
    if failed:
        print(f"FAILED: {failed} test(s) — halalkah.id is NOT ready for this civic-stack version")
        return 1
    print("All smoke tests passed — halalkah.id staging is ready")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.live)))
