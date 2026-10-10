"""Unified MCP registry and entry-point contracts (no portal calls)."""

import json
import logging
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

from civic_stack import server


@pytest.mark.asyncio
async def test_health_matches_registered_tools():
    tools = await server.mcp.list_tools()
    assert len(tools) == 45
    response = await server.health_check(None)
    assert json.loads(response.body) == {
        "status": "ok",
        "server": "indonesia-civic-stack",
        "tools": len(tools),
    }


@pytest.mark.asyncio
async def test_health_count_is_dynamic(monkeypatch):
    monkeypatch.setattr(server.mcp, "list_tools", AsyncMock(return_value=[object(), object()]))
    response = await server.health_check(None)
    assert json.loads(response.body)["tools"] == 2


def test_server_stdio_entrypoint(monkeypatch, caplog):
    monkeypatch.setattr("sys.argv", ["civic-stack-mcp"])
    run = MagicMock()
    monkeypatch.setattr(server.mcp, "run", run)
    monkeypatch.setattr(server.mcp, "list_tools", AsyncMock(return_value=[object()] * 3))
    with caplog.at_level(logging.INFO, logger=server.__name__):
        server.main()
    run.assert_called_once_with(transport="stdio")
    assert "(3 tools)" in caplog.text


def test_server_http_entrypoint(monkeypatch):
    monkeypatch.setattr("sys.argv", ["civic-stack-mcp", "--transport", "http"])
    monkeypatch.setenv("HOST", "127.0.0.2")
    monkeypatch.setenv("PORT", "9001")
    run = MagicMock()
    monkeypatch.setattr(server.mcp, "run", run)
    server.main()
    run.assert_called_once_with(transport="http", host="127.0.0.2", port=9001)


@pytest.mark.asyncio
@pytest.mark.parametrize("args", [["-m", "civic_stack.server"], ["-m", "civic_stack.cli", "mcp"]])
async def test_real_stdio_registry(args):
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    async with Client(StdioTransport(command=sys.executable, args=args), timeout=15) as client:
        tools = await client.list_tools()
    expected = await server.mcp.list_tools()
    assert {tool.name for tool in tools} == {tool.name for tool in expected}


@pytest.mark.asyncio
async def test_real_http_health():
    import httpx

    transport = httpx.ASGITransport(app=server.mcp.http_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["tools"] == len(await server.mcp.list_tools())
