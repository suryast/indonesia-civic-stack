"""
Base class for all indonesia-civic-stack MCP servers.

Every module's MCP server must:
1. Inherit from CivicStackMCPBase
2. Implement the abstract tools using @mcp.tool() decorators
3. Set module_name (either as class attribute or via super().__init__)

Usage — either style works:

    # Style 1: Pass name to __init__
    class BpomMCPServer(CivicStackMCPBase):
        def __init__(self) -> None:
            super().__init__("bpom")

        def _register_tools(self) -> None:
            @self.mcp.tool()
            async def check_bpom(registration_no: str) -> dict: ...

    # Style 2: Class attribute (no __init__ needed)
    class BmkgMCPServer(CivicStackMCPBase):
        module_name = "bmkg"

        def _register_tools(self) -> None:
            @self.mcp.tool()
            async def get_weather(city: str) -> dict: ...
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class CivicStackMCPBase(ABC):
    """
    Abstract base for all civic-stack MCP servers.

    Provides:
    - A FastMCP instance pre-configured with module identity
    - Standard error serialization that keeps MCP tool responses consistent
    - Logging helpers

    Subclasses must call _register_tools() in __init__ to bind their
    @mcp.tool() decorated functions before the server is started.
    """

    module_name: str = ""  # Can be set as class attribute or passed to __init__

    def __init__(self, module_name: str | None = None) -> None:
        # Import here so FastMCP is only required at runtime, not at import time
        # (keeps shared/ importable in envs where fastmcp is not installed)
        try:
            from fastmcp import FastMCP
        except ImportError as exc:
            raise ImportError(
                "fastmcp is required to use CivicStackMCPBase. Install it with: pip install fastmcp"
            ) from exc

        # Support both: __init__("name") and class attribute module_name = "name"
        resolved = module_name or self.module_name
        if not resolved:
            raise ValueError(
                f"{type(self).__name__} must either pass module_name to __init__() "
                "or set module_name as a class attribute."
            )
        self.module_name = resolved
        self.mcp: Any = FastMCP(
            name=f"indonesia-civic-stack/{module_name}",
            instructions=(
                f"MCP server for the '{module_name}' module of indonesia-civic-stack. "
                "All tools return a CivicStackResponse envelope: check `found` and `status` "
                "before reading `result`. Status values: ACTIVE, EXPIRED, SUSPENDED, REVOKED, "
                "NOT_FOUND, ERROR."
            ),
        )
        self._register_tools()
        logger.info("CivicStackMCPBase initialized for module '%s'", module_name)

    @abstractmethod
    def _register_tools(self) -> None:
        """
        Register all @mcp.tool() decorated functions on self.mcp.

        Called automatically by __init__. Subclasses must implement this
        method and use @self.mcp.tool() to expose their lookup functions.
        """

    def serialize_error(self, exc: Exception) -> dict[str, Any]:
        """
        Serialize an exception into a CivicStackResponse-shaped dict for MCP tool error returns.

        MCP tools should return this dict rather than raising, so the AI agent
        can reason about the failure (e.g. ScraperBlockedError vs. NOT_FOUND).
        """
        from shared.schema import error_response

        response = error_response(
            module=self.module_name,
            source_url="",
            detail=str(exc),
        )
        return response.model_dump(mode="json")

    def run(self, transport: str = "stdio") -> None:
        """
        Start the MCP server.

        Args:
            transport: 'stdio' for local/CLI use, 'http' for Railway deployments.
        """
        self.mcp.run(transport=transport)
