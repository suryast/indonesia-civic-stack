"""MCP server for the BPS module."""

from __future__ import annotations

from civic_stack.shared.mcp import CivicStackMCPBase

from .scraper import get_indicator, list_regions, search


class BpsMCPServer(CivicStackMCPBase):
    """MCP server exposing BPS Statistics Indonesia tools."""

    module_name = "bps"

    def _register_tools(self) -> None:

        @self.mcp.tool(
            name="search_bps_datasets",
            description=(
                "Search BPS (Badan Pusat Statistik / Statistics Indonesia) datasets by keyword. "
                "Returns matching subjects/categories from 1,000+ official statistical datasets. "
                "Powers BenarKah fact-checking against official statistics."
            ),
        )
        async def search_bps_datasets(keyword: str) -> list[dict]:
            results = await search(keyword)
            return [r.model_dump(mode="json") for r in results]

        @self.mcp.tool(
            name="get_bps_indicator",
            description=(
                "Get time-series data for a specific BPS indicator by ID. "
                "Optionally filter by region (wilayah code) and year range. "
                "Example: indicator='570' (GDP), region='31' (Jakarta), years='2018,2019,2020'."
            ),
        )
        async def get_bps_indicator(
            indicator_id: str,
            region_code: str = "0000",
            year_range: str | None = None,
        ) -> dict:
            resp = await get_indicator(indicator_id, region_code=region_code, year_range=year_range)
            return resp.model_dump(mode="json")

        @self.mcp.tool(
            name="list_bps_regions",
            description=(
                "List BPS regional codes (wilayah) for use with get_bps_indicator. "
                "Returns province and district/city codes. "
                "Pass parent='0' for all provinces; pass a province code to get its districts."
            ),
        )
        async def list_bps_regions(parent_code: str = "0") -> list[dict]:
            return await list_regions(parent_code)


def main() -> None:
    BpsMCPServer().run("stdio")


if __name__ == "__main__":
    main()
