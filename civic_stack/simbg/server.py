"""MCP server for the SIMBG module."""

from __future__ import annotations

from civic_stack.shared.mcp import CivicStackMCPBase

from .scraper import PILOT_PORTALS, fetch, search


class SimbgMCPServer(CivicStackMCPBase):
    """MCP server exposing SIMBG building permit tools."""

    module_name = "simbg"

    def _register_tools(self) -> None:

        @self.mcp.tool(
            name="lookup_building_permit",
            description=(
                "Look up a building permit (PBG/IMB) by address, permit number, or property ID. "
                "Aggregates data from SIMBG national API and 5 pilot regional portals: "
                "Jakarta, Surabaya, Bandung, Medan, Makassar. "
                "Returns permit type, owner, address, floor area, building function, "
                "issue date, and issuing authority. Powers IzinKah."
            ),
        )
        async def lookup_building_permit(address_or_id: str) -> dict:
            resp = await fetch(address_or_id)
            return resp.model_dump(mode="json")

        @self.mcp.tool(
            name="search_permits_by_area",
            description=(
                "Search building permits across SIMBG portals by area/region keyword. "
                "Returns deduplicated results with confidence score reflecting portal availability. "
                "Confidence < 1.0 indicates some regional portals were unreachable."
            ),
        )
        async def search_permits_by_area(region: str) -> list[dict]:
            results = await search(region)
            return [r.model_dump(mode="json") for r in results]

        @self.mcp.tool(
            name="list_simbg_portals",
            description="List the SIMBG pilot regional portals currently monitored.",
        )
        async def list_simbg_portals() -> list[dict]:
            return PILOT_PORTALS


def main() -> None:
    SimbgMCPServer().run("stdio")


if __name__ == "__main__":
    main()
