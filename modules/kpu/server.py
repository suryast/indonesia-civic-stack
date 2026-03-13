"""KPU MCP server — get_candidate, get_election_results, get_campaign_finance."""

from __future__ import annotations

import argparse

from modules.kpu.scraper import fetch, get_campaign_finance, get_election_results, search
from shared.mcp import CivicStackMCPBase


class KpuMCPServer(CivicStackMCPBase):
    def __init__(self) -> None:
        super().__init__("kpu")

    def _register_tools(self) -> None:
        @self.mcp.tool()
        async def get_candidate(name_or_id: str) -> dict:
            """
            Get a KPU candidate profile by name or ID.

            Returns candidate name, party, election type, region (dapil),
            vote count, and whether they were elected.

            Example: get_candidate("Prabowo Subianto")
            """
            try:
                resp = await fetch(name_or_id)
                return resp.model_dump(mode="json")
            except Exception as exc:
                return self.serialize_error(exc)

        @self.mcp.tool()
        async def search_kpu_candidates(
            name: str,
            election_type: str | None = None,
            party: str | None = None,
        ) -> list[dict]:
            """
            Search KPU candidate registry by name.

            Args:
                name: Candidate name or partial name
                election_type: Filter by "presiden", "dpr", "dpd", "dprd_prov", "dprd_kab"
                party: Filter by party name or abbreviation

            Example: search_kpu_candidates("Budi", election_type="dpr", party="PDIP")
            """
            try:
                filters: dict = {}
                if election_type:
                    filters["election_type"] = election_type
                if party:
                    filters["party"] = party
                results = await search(name, filters=filters or None)
                return [r.model_dump(mode="json") for r in results]
            except Exception as exc:
                return [self.serialize_error(exc)]

        @self.mcp.tool()
        async def get_election_results_kpu(
            region_code: str,
            election_type: str = "dpr",
        ) -> dict:
            """
            Get SIREKAP real-time election results for a region.

            Args:
                region_code: Province/regency code. Use "0" for national totals.
                election_type: "presiden" | "dpr" | "dpd" | "dprd_prov" | "dprd_kab"

            Example: get_election_results_kpu("31", "dpr")  # DKI Jakarta DPR results
            """
            try:
                resp = await get_election_results(region_code, election_type)
                return resp.model_dump(mode="json")
            except Exception as exc:
                return self.serialize_error(exc)

        @self.mcp.tool()
        async def get_campaign_finance_kpu(candidate_id: str) -> dict:
            """
            Get SILON campaign finance report for a KPU candidate.

            Returns initial balance, total income, total expenditure,
            and reporting period from the SILON system.

            Example: get_campaign_finance_kpu("12345")
            """
            try:
                resp = await get_campaign_finance(candidate_id)
                return resp.model_dump(mode="json")
            except Exception as exc:
                return self.serialize_error(exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="KPU MCP server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    args = parser.parse_args()
    KpuMCPServer().run(transport=args.transport)


if __name__ == "__main__":
    main()
