"""MCP server for the BMKG module."""

from __future__ import annotations

from shared.mcp import CivicStackMCPBase

from .scraper import (
    get_alerts,
    get_earthquake_history,
    get_latest_earthquake,
    get_weather_forecast,
)


class BmkgMCPServer(CivicStackMCPBase):
    """MCP server exposing BMKG meteorological and disaster data tools."""

    module_name = "bmkg"

    def _register_tools(self) -> None:

        @self.mcp.tool(
            name="get_bmkg_alerts",
            description=(
                "Get active BMKG (Indonesian weather agency) disaster and weather alerts. "
                "Optionally filter by region name. Returns severity, alert type, and description."
            ),
        )
        async def get_bmkg_alerts(region: str = "") -> list[dict]:
            results = await get_alerts(region)
            return [r.model_dump(mode="json") for r in results]

        @self.mcp.tool(
            name="get_weather_forecast",
            description=(
                "Get a 3-day weather forecast for an Indonesian city from BMKG. "
                "Supported cities: Jakarta, Surabaya, Bandung, Medan, Makassar, Yogyakarta, "
                "Bali/Denpasar, Semarang, Palembang, Pekanbaru, Balikpapan."
            ),
        )
        async def get_weather_forecast_tool(city: str) -> dict:
            resp = await get_weather_forecast(city)
            return resp.model_dump(mode="json")

        @self.mcp.tool(
            name="get_earthquake_history",
            description=(
                "Get recent significant earthquake history from BMKG's seismology database. "
                "Returns magnitude, depth, coordinates, region, and tsunami potential. "
                "Optionally filter by region name (e.g. 'Sulawesi', 'Papua')."
            ),
        )
        async def get_earthquake_history_tool(region: str = "", days: int = 7) -> list[dict]:
            results = await get_earthquake_history(region, days=days)
            return [r.model_dump(mode="json") for r in results]

        @self.mcp.tool(
            name="get_latest_earthquake",
            description="Get the most recent significant earthquake recorded by BMKG.",
        )
        async def get_latest_earthquake_tool() -> dict:
            resp = await get_latest_earthquake()
            return resp.model_dump(mode="json")


def main() -> None:
    BmkgMCPServer().run("stdio")


if __name__ == "__main__":
    main()
