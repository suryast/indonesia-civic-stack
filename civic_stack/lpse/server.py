"""MCP server for the LPSE module."""

from __future__ import annotations

from civic_stack.shared.mcp import CivicStackMCPBase

from .scraper import fetch, search, search_tenders


class LpseMCPServer(CivicStackMCPBase):
    """MCP server exposing LPSE procurement data tools."""

    module_name = "lpse"

    def _register_tools(self) -> None:

        @self.mcp.tool(
            name="lookup_vendor_lpse",
            description=(
                "Look up a vendor or company in LPSE (government procurement portals) "
                "by name or NPWP (tax ID). Returns aggregated results from 5 major portals "
                "with confidence score reflecting portal availability."
            ),
        )
        async def lookup_vendor_lpse(query: str) -> dict:
            resp = await fetch(query)
            return resp.model_dump(mode="json")

        @self.mcp.tool(
            name="search_lpse_vendors",
            description=(
                "Search for vendors/companies across all LPSE portals. "
                "Returns deduplicated list with partial results if some portals are unreachable."
            ),
        )
        async def search_lpse_vendors(keyword: str) -> list[dict]:
            results = await search(keyword)
            return [r.model_dump(mode="json") for r in results]

        @self.mcp.tool(
            name="search_lpse_tenders",
            description=(
                "Search for active procurement tenders across all LPSE portals by keyword. "
                "Returns tender details including ceiling value, HPS, procurement method, and stage."
            ),
        )
        async def search_lpse_tenders(keyword: str) -> list[dict]:
            results = await search_tenders(keyword)
            return [r.model_dump(mode="json") for r in results]

        @self.mcp.tool(
            name="get_lpse_portals",
            description="List all LPSE portals monitored by this module.",
        )
        async def get_lpse_portals() -> list[dict]:
            from .scraper import PORTALS

            return PORTALS


def main() -> None:
    LpseMCPServer().run("stdio")


if __name__ == "__main__":
    main()
