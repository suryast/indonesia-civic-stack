"""
CLI entry point for indonesia-civic-stack.

Usage:
    civic-stack --version
    civic-stack mcp         # Start unified MCP server (40 tools)
    civic-stack api         # Start REST API server
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="civic-stack",
        description="indonesia-civic-stack — Python SDK for Indonesian government data",
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"%(prog)s {_get_version()}",
    )
    subparsers = parser.add_subparsers(dest="command")

    # MCP server
    mcp_parser = subparsers.add_parser("mcp", help="Start unified MCP server (40 tools)")
    mcp_parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
    )

    # API server
    api_parser = subparsers.add_parser("api", help="Start REST API server")
    api_parser.add_argument("--port", type=int, default=8000)
    api_parser.add_argument("--host", default="0.0.0.0")

    args = parser.parse_args()

    if args.command == "mcp":
        from civic_stack.server import create_mcp_server

        mcp = create_mcp_server()
        mcp.run(transport=args.transport)
    elif args.command == "api":
        try:
            import uvicorn
        except ImportError:
            print("uvicorn required: pip install indonesia-civic-stack[api]", file=sys.stderr)
            sys.exit(1)
        uvicorn.run("civic_stack.app:app", host=args.host, port=args.port)
    else:
        parser.print_help()


def _get_version() -> str:
    try:
        from civic_stack import __version__

        return __version__
    except ImportError:
        return "unknown"


if __name__ == "__main__":
    main()
