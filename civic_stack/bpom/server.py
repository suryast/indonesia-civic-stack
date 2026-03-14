"""
BPOM MCP server — exposes check_bpom, search_bpom, get_bpom_status.

Usage (stdio, local):
    python -m modules.bpom.server

Usage (HTTP, Railway):
    python -m modules.bpom.server --transport http
"""

from __future__ import annotations

import argparse

from civic_stack.bpom.scraper import fetch, search
from civic_stack.shared.mcp import CivicStackMCPBase


class BpomMCPServer(CivicStackMCPBase):
    def __init__(self) -> None:
        super().__init__("bpom")

    def _register_tools(self) -> None:
        @self.mcp.tool()
        async def check_bpom(registration_no: str) -> dict:
            """
            Look up a BPOM product registration by registration number.

            Returns a CivicStackResponse envelope. Check `found` and `status`
            before reading `result`. Status values: ACTIVE, EXPIRED, REVOKED,
            SUSPENDED, NOT_FOUND, ERROR.

            Example: check_bpom("BPOM MD 123456789012")
            """
            try:
                resp = await fetch(registration_no)
                return resp.model_dump(mode="json")
            except Exception as exc:
                return self.serialize_error(exc)

        @self.mcp.tool()
        async def search_bpom(product_name: str) -> list[dict]:
            """
            Search the BPOM product registry by product name or keyword.

            Returns a list of CivicStackResponse envelopes (may be empty).
            Each result has `confidence` < 1.0 since search results are
            fuzzy matches — verify with check_bpom() for exact confirmation.

            Example: search_bpom("paracetamol")
            """
            try:
                results = await search(product_name)
                return [r.model_dump(mode="json") for r in results]
            except Exception as exc:
                return [self.serialize_error(exc)]

        @self.mcp.tool()
        async def get_bpom_status(registration_no: str) -> dict:
            """
            Get the registration status of a BPOM product (lighter than check_bpom).

            Returns status (ACTIVE/EXPIRED/REVOKED/SUSPENDED/NOT_FOUND/ERROR)
            and expiry date without fetching the full product record.

            Example: get_bpom_status("BPOM MD 123456789012")
            """
            try:
                resp = await fetch(registration_no)
                return {
                    "registration_no": registration_no,
                    "status": resp.status,
                    "found": resp.found,
                    "expiry_date": resp.result.get("expiry_date") if resp.result else None,
                    "product_name": resp.result.get("product_name") if resp.result else None,
                    "confidence": resp.confidence,
                    "fetched_at": resp.fetched_at.isoformat(),
                    "module": resp.module,
                }
            except Exception as exc:
                return self.serialize_error(exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="BPOM MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="MCP transport (stdio for local, http for Railway)",
    )
    args = parser.parse_args()
    BpomMCPServer().run(transport=args.transport)


if __name__ == "__main__":
    main()
