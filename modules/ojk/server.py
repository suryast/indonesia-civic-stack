"""OJK MCP server — check_ojk_license, search_ojk_institutions, get_ojk_status."""

from __future__ import annotations

import argparse

from modules.ojk.scraper import check_waspada, fetch, search
from shared.mcp import CivicStackMCPBase


class OjkMCPServer(CivicStackMCPBase):
    def __init__(self) -> None:
        super().__init__("ojk")

    def _register_tools(self) -> None:
        @self.mcp.tool()
        async def check_ojk_license(name_or_id: str) -> dict:
            """
            Check if a financial institution is licensed by OJK.

            Covers banks (Bank Umum, BPR), fintech (P2P, payment),
            insurance, pension funds, investment managers, securities firms.

            Returns license number, institution type, status, and products.
            Status ACTIVE = validly licensed. REVOKED/SUSPENDED = danger signal.

            Example: check_ojk_license("PT Akulaku Finance Indonesia")
            """
            try:
                return (await fetch(name_or_id)).model_dump(mode="json")
            except Exception as exc:
                return self.serialize_error(exc)

        @self.mcp.tool()
        async def search_ojk_institutions(
            keyword: str,
            institution_type: str | None = None,
        ) -> list[dict]:
            """
            Search OJK licensed institution registry by keyword.

            Args:
                keyword: Institution name or partial name
                institution_type: Optional filter — "bank_umum", "bpr",
                    "fintech_p2p", "fintech_payment", "asuransi",
                    "dana_pensiun", "manajer_investasi", "sekuritas"

            Example: search_ojk_institutions("Akulaku", institution_type="fintech_p2p")
            """
            try:
                filters = {"institution_type": institution_type} if institution_type else None
                results = await search(keyword, filters=filters)
                return [r.model_dump(mode="json") for r in results]
            except Exception as exc:
                return [self.serialize_error(exc)]

        @self.mcp.tool()
        async def get_ojk_status(name_or_id: str) -> dict:
            """
            Get OJK license status for an institution (lighter than check_ojk_license).

            Returns only institution name, license number, type, and status.
            Use this for quick license validity checks.

            Example: get_ojk_status("Bank Central Asia")
            """
            try:
                resp = await fetch(name_or_id)
                return {
                    "institution_name": name_or_id,
                    "status": resp.status,
                    "found": resp.found,
                    "license_status": resp.result.get("license_status") if resp.result else None,
                    "institution_type": resp.result.get("institution_type") if resp.result else None,
                    "license_no": resp.result.get("license_no") if resp.result else None,
                    "confidence": resp.confidence,
                    "fetched_at": resp.fetched_at.isoformat(),
                    "module": resp.module,
                }
            except Exception as exc:
                return self.serialize_error(exc)

        @self.mcp.tool()
        async def check_ojk_waspada(entity_name: str) -> dict:
            """
            Check if an entity is on OJK's Waspada Investasi (investment alert) list.

            Waspada Investasi flags unlicensed or potentially fraudulent
            investment entities. Returns NOT_FOUND if the entity is clean.
            Returns SUSPENDED (found on alert list) if flagged.

            Example: check_ojk_waspada("PT Untung Berlipat Investasi")
            """
            try:
                return (await check_waspada(entity_name)).model_dump(mode="json")
            except Exception as exc:
                return self.serialize_error(exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="OJK MCP server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    args = parser.parse_args()
    OjkMCPServer().run(transport=args.transport)


if __name__ == "__main__":
    main()
