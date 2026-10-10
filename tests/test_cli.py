"""Offline CLI contracts: metadata and transport-specific binding options."""

import importlib.metadata
import runpy
import sys
from unittest.mock import MagicMock

import pytest

from civic_stack import __version__, cli


def test_version_matches_distribution(capsys):
    assert __version__ == importlib.metadata.version("indonesia-civic-stack")
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"civic-stack {__version__}"


@pytest.mark.parametrize("installed", [True, False])
def test_version_metadata_and_uninstalled_fallback(monkeypatch, installed):
    import civic_stack

    def metadata_version(name):
        assert name == "indonesia-civic-stack"
        if not installed:
            raise importlib.metadata.PackageNotFoundError(name)
        return "1.2.0"

    monkeypatch.setattr(importlib.metadata, "version", metadata_version)
    namespace = runpy.run_path(civic_stack.__file__)
    assert namespace["__version__"] == ("1.2.0" if installed else "0+unknown")


@pytest.mark.parametrize("command", ["mcp", "api"])
@pytest.mark.parametrize("explicit", [False, True])
def test_http_binding(monkeypatch, command, explicit):
    from civic_stack import server

    monkeypatch.setenv("HOST", "127.0.0.2")
    monkeypatch.setenv("PORT", "9001")
    run = MagicMock()
    monkeypatch.setattr(server.mcp, "run", run)
    uvicorn = MagicMock()
    monkeypatch.setitem(sys.modules, "uvicorn", uvicorn)
    args = [command]
    if command == "mcp":
        args += ["--transport", "http"]
    if explicit:
        args += ["--host", "127.0.0.3", "--port", "9002"]
    cli.main(args)
    binding = {"host": "127.0.0.3" if explicit else "127.0.0.2", "port": 9002 if explicit else 9001}
    if command == "mcp":
        run.assert_called_once_with(transport="http", **binding)
    else:
        uvicorn.run.assert_called_once_with("civic_stack.app:app", **binding)


def test_stdio_ignores_http_binding(monkeypatch):
    from civic_stack import server

    run = MagicMock()
    monkeypatch.setattr(server.mcp, "run", run)
    cli.main(["mcp", "--host", "127.0.0.2", "--port", "9001"])
    run.assert_called_once_with(transport="stdio")


def test_http_default_binding(monkeypatch):
    from civic_stack import server

    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    run = MagicMock()
    monkeypatch.setattr(server.mcp, "run", run)
    cli.main(["mcp", "--transport", "http"])
    run.assert_called_once_with(transport="http", host="0.0.0.0", port=8000)
