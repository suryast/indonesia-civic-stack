"""
Unified MCP server entry point (backwards-compatible).

For new installs, use: civic-stack-mcp
Or: python -m civic_stack.server
"""

from civic_stack.server import main, mcp  # noqa: F401

if __name__ == "__main__":
    main()
