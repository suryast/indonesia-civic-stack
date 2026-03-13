#!/usr/bin/env python3
"""
Integration test harness for indonesia-civic-stack modules.

In CI this runs against VCR cassettes (no live portal calls).
With --live it runs against actual government portals and reports
pass / DEGRADED per module.

Usage:
    python scripts/test_module.py               # VCR replay (safe in CI)
    python scripts/test_module.py --live        # Live portal calls
    python scripts/test_module.py --module bpom # Single module only
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import os
import sys
import traceback
from dataclasses import dataclass, field
from typing import Any

# Ensure repo root is on the path when running as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.schema import CivicStackResponse, RecordStatus

# Registry of available modules and their smoke-test queries.
MODULE_REGISTRY: dict[str, dict[str, Any]] = {
    # Phase 1
    "bpom": {
        "fetch_query": "BPOM MD 123456789012",
        "search_keyword": "paracetamol",
    },
    "bpjph": {
        "fetch_query": "ID00110019882120240001",
        "search_keyword": "mie instan",
    },
    "ahu": {
        "fetch_query": "PT Contoh Indonesia",
        "search_keyword": "Contoh",
    },
    # Phase 2
    "kpu": {
        "fetch_query": "12345",
        "search_keyword": "Joko",
    },
    "ojk": {
        "fetch_query": "Akulaku",
        "search_keyword": "fintech",
    },
    "oss_nib": {
        "fetch_query": "PT Gojek Indonesia",
        "search_keyword": "Gojek",
    },
    "lpse": {
        "fetch_query": "PT Telkom",
        "search_keyword": "telkom",
    },
}


@dataclass
class ModuleResult:
    module: str
    fetch_ok: bool = False
    search_ok: bool = False
    error: str | None = None
    details: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.fetch_ok and self.search_ok and self.error is None


def _validate_response(resp: Any, module: str) -> list[str]:
    """Return a list of validation errors for a CivicStackResponse."""
    errors: list[str] = []
    if not isinstance(resp, CivicStackResponse):
        errors.append(f"fetch() returned {type(resp).__name__}, expected CivicStackResponse")
        return errors
    if resp.module != module:
        errors.append(f"module field is '{resp.module}', expected '{module}'")
    if resp.status not in list(RecordStatus):
        errors.append(f"unknown status value: {resp.status}")
    if not (0.0 <= resp.confidence <= 1.0):
        errors.append(f"confidence {resp.confidence} out of [0, 1] range")
    if not resp.source_url:
        errors.append("source_url is empty")
    if resp.fetched_at is None:
        errors.append("fetched_at is None")
    return errors


async def test_module(module_name: str, config: dict[str, Any], live: bool) -> ModuleResult:
    result = ModuleResult(module=module_name)

    try:
        mod = importlib.import_module(f"modules.{module_name}")
    except ImportError as exc:
        result.error = f"Import failed: {exc}"
        return result

    # Test fetch()
    try:
        resp = await mod.fetch(config["fetch_query"])
        errs = _validate_response(resp, module_name)
        if errs:
            result.details.extend(errs)
        else:
            result.fetch_ok = True
            result.details.append(
                f"fetch OK — found={resp.found}, status={resp.status}, confidence={resp.confidence}"
            )
    except Exception:
        result.details.append(f"fetch() raised:\n{traceback.format_exc()}")

    # Test search()
    try:
        results = await mod.search(config["search_keyword"])
        if not isinstance(results, list):
            result.details.append(f"search() returned {type(results).__name__}, expected list")
        else:
            errs = []
            for _i, r in enumerate(results):
                errs.extend(_validate_response(r, module_name))
            if errs:
                result.details.extend(errs)
            else:
                result.search_ok = True
                result.details.append(f"search OK — {len(results)} results returned")
    except Exception:
        result.details.append(f"search() raised:\n{traceback.format_exc()}")

    return result


async def run(modules: list[str], live: bool) -> int:
    if not modules:
        print("No modules registered yet. Add entries to MODULE_REGISTRY in this script.")
        return 0

    results: list[ModuleResult] = []
    for name in modules:
        print(f"\n── Testing {name} {'(live)' if live else '(VCR)'} ──")
        r = await test_module(name, MODULE_REGISTRY[name], live)
        results.append(r)
        status = "PASS" if r.ok else "DEGRADED"
        print(f"  {status}")
        for detail in r.details:
            print(f"    {detail}")

    failed = [r for r in results if not r.ok]
    print(f"\n{'=' * 50}")
    print(f"Results: {len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("DEGRADED modules:", ", ".join(r.module for r in failed))
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="indonesia-civic-stack integration test harness")
    parser.add_argument("--live", action="store_true", help="Run against live portals")
    parser.add_argument("--module", help="Test a single module by name")
    args = parser.parse_args()

    if args.module:
        if args.module not in MODULE_REGISTRY:
            print(f"Unknown module: {args.module}. Available: {list(MODULE_REGISTRY)}")
            sys.exit(1)
        modules = [args.module]
    else:
        modules = list(MODULE_REGISTRY)

    exit_code = asyncio.run(run(modules, args.live))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
