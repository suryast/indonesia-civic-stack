"""AHU MCP server — lookup_company_ahu, get_company_directors, verify_company_status."""

from __future__ import annotations

import argparse

from modules.ahu.scraper import fetch, search
from shared.mcp import CivicStackMCPBase


class AhuMCPServer(CivicStackMCPBase):
    def __init__(self) -> None:
        super().__init__("ahu")

    def _register_tools(self) -> None:
        @self.mcp.tool()
        async def lookup_company_ahu(name_or_id: str, proxy_url: str | None = None) -> dict:
            """
            Look up a company in the AHU (Kemenkumham) company registry.

            Returns full company detail including legal form, status, directors,
            commissioners, deed date, and domicile.

            IMPORTANT: AHU blocks datacenter IPs. Supply proxy_url if running
            from a cloud environment. See module README for Cloudflare Worker setup.

            Example: lookup_company_ahu("PT Contoh Indonesia Tbk")
            """
            try:
                resp = await fetch(name_or_id, proxy_url=proxy_url)
                return resp.model_dump(mode="json")
            except Exception as exc:
                return self.serialize_error(exc)

        @self.mcp.tool()
        async def get_company_directors(company_id: str, proxy_url: str | None = None) -> dict:
            """
            Get the directors (Direksi) and commissioners (Dewan Komisaris) of a company.

            Returns a CivicStackResponse with directors and commissioners lists
            in the result field. Useful for corporate graph and ownership analysis.

            Example: get_company_directors("PT Contoh Indonesia Tbk")
            """
            try:
                resp = await fetch(company_id, proxy_url=proxy_url)
                if resp.result:
                    return {
                        "company_name": resp.result.get("company_name"),
                        "registration_no": resp.result.get("registration_no"),
                        "directors": resp.result.get("directors", []),
                        "commissioners": resp.result.get("commissioners", []),
                        "found": resp.found,
                        "status": resp.status,
                        "confidence": resp.confidence,
                        "fetched_at": resp.fetched_at.isoformat(),
                        "module": resp.module,
                    }
                return resp.model_dump(mode="json")
            except Exception as exc:
                return self.serialize_error(exc)

        @self.mcp.tool()
        async def verify_company_status(company_id: str, proxy_url: str | None = None) -> dict:
            """
            Verify the legal status of a company registered in AHU.

            Returns status (ACTIVE/REVOKED/SUSPENDED/NOT_FOUND/ERROR),
            legal form (PT/CV/Yayasan/etc.), registration number, and deed date.

            Example: verify_company_status("PT Contoh Indonesia Tbk")
            """
            try:
                resp = await fetch(company_id, proxy_url=proxy_url)
                return {
                    "company_name": company_id,
                    "status": resp.status,
                    "found": resp.found,
                    "legal_form": resp.result.get("legal_form") if resp.result else None,
                    "legal_status": resp.result.get("legal_status") if resp.result else None,
                    "registration_no": resp.result.get("registration_no") if resp.result else None,
                    "deed_date": resp.result.get("deed_date") if resp.result else None,
                    "domicile": resp.result.get("domicile") if resp.result else None,
                    "confidence": resp.confidence,
                    "fetched_at": resp.fetched_at.isoformat(),
                    "module": resp.module,
                }
            except Exception as exc:
                return self.serialize_error(exc)

        @self.mcp.tool()
        async def search_companies_ahu(keyword: str, proxy_url: str | None = None) -> list[dict]:
            """
            Search AHU company registry by keyword.

            Returns up to 10 results. Each result has lower confidence (0.7-0.8)
            than a direct lookup — use lookup_company_ahu() for exact verification.

            Example: search_companies_ahu("Contoh Indonesia")
            """
            try:
                results = await search(keyword, proxy_url=proxy_url)
                return [r.model_dump(mode="json") for r in results]
            except Exception as exc:
                return [self.serialize_error(exc)]


def main() -> None:
    parser = argparse.ArgumentParser(description="AHU MCP server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    args = parser.parse_args()
    AhuMCPServer().run(transport=args.transport)


if __name__ == "__main__":
    main()
