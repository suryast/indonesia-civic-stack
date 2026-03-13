"""MCP server for the LHKPN module."""

from __future__ import annotations

from shared.mcp import CivicStackMCPBase

from .scraper import compare_lhkpn, fetch, get_pdf, search


class LhkpnMCPServer(CivicStackMCPBase):
    """MCP server exposing KPK wealth declaration tools."""

    module_name = "lhkpn"

    def _register_tools(self) -> None:

        @self.mcp.tool(
            name="get_lhkpn",
            description=(
                "Look up an Indonesian public official's LHKPN (wealth declaration) by name. "
                "Returns latest declaration with total assets, liabilities, net worth, and "
                "asset breakdown. Powers DPR Watch and TerpercayaKah profiles."
            ),
        )
        async def get_lhkpn(official_name: str) -> dict:
            resp = await fetch(official_name)
            return resp.model_dump(mode="json")

        @self.mcp.tool(
            name="search_lhkpn",
            description=(
                "Search LHKPN declarations by official name, ministry, or position keyword. "
                "Returns list of matching officials with their latest declaration summaries."
            ),
        )
        async def search_lhkpn(ministry_or_name: str) -> list[dict]:
            results = await search(ministry_or_name)
            return [r.model_dump(mode="json") for r in results]

        @self.mcp.tool(
            name="compare_lhkpn",
            description=(
                "Compare two LHKPN declarations for the same official across different years. "
                "Returns the delta in total assets, liabilities, and net worth — useful for "
                "detecting unexplained wealth increases."
            ),
        )
        async def compare_lhkpn_tool(
            official_id: str, year_a: int, year_b: int
        ) -> dict:
            return await compare_lhkpn(official_id, year_a, year_b)

        @self.mcp.tool(
            name="get_lhkpn_pdf",
            description=(
                "Download and extract a specific LHKPN PDF by report ID. "
                "Uses pdfplumber for text-layer PDFs; falls back to Claude Vision API "
                "for scanned/image PDFs. Requires the [pdf] extra."
            ),
        )
        async def get_lhkpn_pdf(report_id: str) -> dict:
            return await get_pdf(report_id)


def main() -> None:
    LhkpnMCPServer().run("stdio")


if __name__ == "__main__":
    main()
