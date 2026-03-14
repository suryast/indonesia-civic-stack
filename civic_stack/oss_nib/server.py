"""OSS-NIB MCP server — lookup_nib, verify_nib."""

from __future__ import annotations

import argparse

from civic_stack.oss_nib.scraper import fetch, search
from civic_stack.shared.mcp import CivicStackMCPBase


class OssNibMCPServer(CivicStackMCPBase):
    def __init__(self) -> None:
        super().__init__("oss_nib")

    def _register_tools(self) -> None:
        @self.mcp.tool()
        async def lookup_nib(company_name: str, proxy_url: str | None = None) -> dict:
            """
            Look up a business by company name in OSS RBA (NIB registry).

            Returns NIB number, business classification (KBLI), risk level,
            license status, and domicile from the OSS public search tier.

            Example: lookup_nib("PT Gojek Indonesia")
            """
            try:
                return (await fetch(company_name, proxy_url=proxy_url)).model_dump(mode="json")
            except Exception as exc:
                return self.serialize_error(exc)

        @self.mcp.tool()
        async def verify_nib(nib_number: str, proxy_url: str | None = None) -> dict:
            """
            Verify a NIB (Nomor Induk Berusaha) number and return its status.

            NIB is a 13-digit business identity number issued by OSS.
            Returns company name, risk level, and current license status.

            Example: verify_nib("1234567890123")
            """
            try:
                resp = await fetch(nib_number, proxy_url=proxy_url)
                return {
                    "nib": nib_number,
                    "status": resp.status,
                    "found": resp.found,
                    "company_name": resp.result.get("company_name") if resp.result else None,
                    "risk_level": resp.result.get("risk_level") if resp.result else None,
                    "license_status": resp.result.get("license_status") if resp.result else None,
                    "confidence": resp.confidence,
                    "fetched_at": resp.fetched_at.isoformat(),
                    "module": resp.module,
                }
            except Exception as exc:
                return self.serialize_error(exc)

        @self.mcp.tool()
        async def search_oss_businesses(keyword: str, proxy_url: str | None = None) -> list[dict]:
            """
            Search OSS business registry by company name keyword.

            Returns up to 10 results from the OSS public search tier.
            Each result includes NIB, company name, risk level, and status.

            Example: search_oss_businesses("Gojek")
            """
            try:
                results = await search(keyword, proxy_url=proxy_url)
                return [r.model_dump(mode="json") for r in results]
            except Exception as exc:
                return [self.serialize_error(exc)]


def main() -> None:
    parser = argparse.ArgumentParser(description="OSS-NIB MCP server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    args = parser.parse_args()
    OssNibMCPServer().run(transport=args.transport)


if __name__ == "__main__":
    main()
