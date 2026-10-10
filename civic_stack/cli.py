"""CLI entry point for the SDK, unified MCP server, and REST API."""

from __future__ import annotations

import argparse
import os
import sys


def _add_http_arguments(parser: argparse.ArgumentParser) -> None:
    """Share deployment defaults across both HTTP entry points."""
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "0.0.0.0"),
        help="HTTP bind host (default: HOST env var or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=os.environ.get("PORT", "8000"),
        help="HTTP bind port (default: PORT env var or 8000)",
    )


def _add_mcp_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    _add_http_arguments(parser)


def main(argv: list[str] | None = None) -> None:
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
    mcp_parser = subparsers.add_parser("mcp", help="Start unified MCP server")
    _add_mcp_arguments(mcp_parser)
    api_parser = subparsers.add_parser("api", help="Start REST API server")
    _add_http_arguments(api_parser)
    args = parser.parse_args(argv)

    if args.command == "mcp":
        from civic_stack.server import run_mcp_server

        run_mcp_server(transport=args.transport, host=args.host, port=args.port)
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
    from civic_stack import __version__

    return __version__


if __name__ == "__main__":
    main()
