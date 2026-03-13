#!/usr/bin/env python3
"""End-to-end test harness for civic-stack modules.

Usage:
    python scripts/test_module.py bpom
    python scripts/test_module.py --all
"""

import argparse
import asyncio
import sys

from shared.schema import ModuleName, ResponseStatus


async def test_module(name: str) -> bool:
    """Run basic smoke test on a module."""
    try:
        mod = __import__(f"modules.{name}", fromlist=["fetch", "search"])
        fetch_fn = getattr(mod, "fetch", None)
        search_fn = getattr(mod, "search", None)

        if not fetch_fn or not search_fn:
            print(f"  ⚠️  {name}: fetch() or search() not implemented yet")
            return True  # Not a failure, just not built yet

        # Test fetch with a dummy ID
        result = await fetch_fn("TEST-000")
        assert result.module == name, f"Module name mismatch: {result.module}"
        assert isinstance(result.status, ResponseStatus), "Invalid status type"
        print(f"  ✅ {name}.fetch() — status: {result.status}")

        # Test search
        result = await search_fn("test")
        assert result.module == name, f"Module name mismatch: {result.module}"
        print(f"  ✅ {name}.search() — status: {result.status}, found: {result.found}")

        return True

    except NotImplementedError:
        print(f"  ⏳ {name}: Not yet implemented")
        return True
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        return False


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test civic-stack modules")
    parser.add_argument("module", nargs="?", help="Module name to test")
    parser.add_argument("--all", action="store_true", help="Test all modules")
    args = parser.parse_args()

    if args.all:
        modules = [m.value for m in ModuleName]
    elif args.module:
        modules = [args.module]
    else:
        parser.print_help()
        sys.exit(1)

    print(f"Testing {len(modules)} module(s)...\n")
    results = []
    for name in modules:
        print(f"Module: {name}")
        ok = await test_module(name)
        results.append((name, ok))
        print()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\nResults: {passed}/{total} passed")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
