"""BPJPH MCP server — check_halal_cert, lookup_halal_by_product, get_halal_status."""

from __future__ import annotations

import argparse

from modules.bpjph.scraper import cross_ref_bpom, fetch, search
from shared.mcp import CivicStackMCPBase


class BpjphMCPServer(CivicStackMCPBase):
    def __init__(self) -> None:
        super().__init__("bpjph")

    def _register_tools(self) -> None:
        @self.mcp.tool()
        async def check_halal_cert(cert_no: str) -> dict:
            """
            Look up a BPJPH halal certificate by certificate number.

            Returns a CivicStackResponse envelope. Check `found` and `status`.
            Status values: ACTIVE, EXPIRED, REVOKED, SUSPENDED, NOT_FOUND, ERROR.

            Example: check_halal_cert("BPJPH-00001-2023")
            """
            try:
                resp = await fetch(cert_no)
                return resp.model_dump(mode="json")
            except Exception as exc:
                return self.serialize_error(exc)

        @self.mcp.tool()
        async def lookup_halal_by_product(product_name: str) -> list[dict]:
            """
            Search for halal certificates by product name or company name.

            Returns a list of CivicStackResponse envelopes (may be empty).
            Use check_halal_cert() for exact certificate number lookups.

            Example: lookup_halal_by_product("mie instan")
            """
            try:
                results = await search(product_name)
                return [r.model_dump(mode="json") for r in results]
            except Exception as exc:
                return [self.serialize_error(exc)]

        @self.mcp.tool()
        async def get_halal_status(company_name: str) -> list[dict]:
            """
            Get halal certification status for all products of a company.

            Returns a list of CivicStackResponse envelopes, one per certificate.
            Useful for checking whether a company's halal certs are still valid.

            Example: get_halal_status("PT Indofood Sukses Makmur")
            """
            try:
                results = await search(company_name)
                return [r.model_dump(mode="json") for r in results]
            except Exception as exc:
                return [self.serialize_error(exc)]

        @self.mcp.tool()
        async def cross_reference_halal_bpom(product_name: str) -> dict:
            """
            Cross-reference a product between BPJPH (halal cert) and BPOM (registration).

            Runs both lookups and returns a combined result highlighting any mismatch:
            - BPOM registration ACTIVE but halal cert EXPIRED
            - Halal cert ACTIVE but BPOM registration EXPIRED

            This is the primary HalalKah verification tool.

            Example: cross_reference_halal_bpom("mie goreng spesial")
            """
            try:
                return await cross_ref_bpom(product_name)
            except Exception as exc:
                return self.serialize_error(exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="BPJPH MCP server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    args = parser.parse_args()
    BpjphMCPServer().run(transport=args.transport)


if __name__ == "__main__":
    main()
