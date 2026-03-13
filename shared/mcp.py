"""Base MCP server class for civic-stack modules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from fastmcp import FastMCP

from shared.schema import CivicStackResponse, ModuleName


class CivicStackMCPBase(ABC):
    """Abstract base class every module MCP server inherits.

    Subclasses must implement:
        - module_name: ModuleName identifying this module
        - fetch(): single-record lookup by ID
        - search(): multi-record search by query

    The base class handles MCP server setup, tool registration,
    and response envelope wrapping.
    """

    module_name: ModuleName
    description: str = ""

    def __init__(self) -> None:
        self.mcp = FastMCP(
            name=f"civic-stack-{self.module_name}",
            description=self.description or f"Indonesian {self.module_name.upper()} data lookup",
        )
        self._register_tools()

    @abstractmethod
    async def fetch(self, identifier: str) -> CivicStackResponse:
        """Fetch a single record by its identifier (registration number, cert number, etc.)."""
        ...

    @abstractmethod
    async def search(self, query: str, page: int = 1, limit: int = 20) -> CivicStackResponse:
        """Search for records matching a query string."""
        ...

    def _register_tools(self) -> None:
        """Register fetch and search as MCP tools. Subclasses can override to add more."""

        @self.mcp.tool(
            name=f"check_{self.module_name}",
            description=f"Look up a single {self.module_name.upper()} record by ID",
        )
        async def check(identifier: str) -> dict[str, Any]:
            result = await self.fetch(identifier)
            return result.model_dump(mode="json", exclude_none=True)

        @self.mcp.tool(
            name=f"search_{self.module_name}",
            description=f"Search {self.module_name.upper()} records by name or keyword",
        )
        async def search_tool(query: str, page: int = 1, limit: int = 20) -> dict[str, Any]:
            result = await self.search(query, page=page, limit=limit)
            return result.model_dump(mode="json", exclude_none=True)

    def run(self, transport: str = "streamable-http", host: str = "0.0.0.0", port: int = 8000) -> None:
        """Start the MCP server."""
        self.mcp.run(transport=transport, host=host, port=port)
