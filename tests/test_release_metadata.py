"""Keep public release metadata and the installable skill in sync (offline)."""

import ast
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_core_import_does_not_load_optional_browser_dependencies():
    script = """
import sys
import civic_stack
assert 'playwright' not in sys.modules
assert 'civic_stack.jdih.scraper' not in sys.modules
from civic_stack import bpom
assert callable(bpom.search)
assert 'civic_stack.jdih.scraper' not in sys.modules
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_release_versions_match():
    from civic_stack import __version__

    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    server = json.loads((ROOT / "server.json").read_text())
    assert __version__ == project["version"] == server["version"]
    assert all(package["version"] == project["version"] for package in server["packages"])


def test_portable_skill_frontmatter():
    text = (ROOT / "SKILL.md").read_text()
    assert text.startswith("---\n")
    frontmatter = yaml.safe_load(text.split("---", 2)[1])
    assert isinstance(frontmatter, dict)
    assert set(frontmatter) <= {
        "name",
        "description",
        "license",
        "compatibility",
        "metadata",
        "allowed-tools",
    }
    name = frontmatter["name"]
    assert name == "indonesia-civic-stack"
    assert len(name) <= 64 and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)
    assert isinstance(frontmatter["description"], str)
    assert 1 <= len(frontmatter["description"]) <= 1024
    if "compatibility" in frontmatter:
        assert isinstance(frontmatter["compatibility"], str)
        assert 1 <= len(frontmatter["compatibility"]) <= 500
    metadata = frontmatter.get("metadata", {})
    assert isinstance(metadata, dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in metadata.items())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert metadata["version"] == project["version"]
    for link in re.findall(r"\]\(([^)]+)\)", text):
        if "://" not in link and not link.startswith("#"):
            path = (ROOT / link.split("#", 1)[0]).resolve()
            assert path.is_relative_to(ROOT)
            assert path.exists(), f"Missing skill resource: {link}"


def test_public_inventory_matches_implementation():
    modules = sorted(path.parent.name for path in (ROOT / "civic_stack").glob("*/scraper.py"))
    tree = ast.parse((ROOT / "civic_stack/server.py").read_text())
    tools = [
        node.name
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef)
        and any(
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and isinstance(decorator.func.value, ast.Name)
            and decorator.func.value.id == "mcp"
            and decorator.func.attr == "tool"
            for decorator in node.decorator_list
        )
    ]
    assert len(tools) == len(set(tools))
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert f"{len(tools)} MCP tools" in project["description"]
    assert f"{len(modules)} Indonesian" in project["description"]
    skill = (ROOT / "SKILL.md").read_text()
    assert "references/usage.md" in skill
    usage = (ROOT / "references/usage.md").read_text()
    for module in modules:
        assert module in usage, f"Undocumented module: {module}"


@pytest.mark.parametrize("filename", ["SKILL.md", "README.md", "AGENTS.md", "CLAUDE.md"])
def test_public_guidance_uses_current_package(filename):
    text = (ROOT / filename).read_text()
    assert "modules.bpom" not in text
    assert "mypy shared/" not in text
    assert 'pip install ".[playwright]"' not in text
