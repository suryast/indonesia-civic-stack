"""Caller-supplied proxy URLs must be operator-configured (no portal calls)."""

import importlib

import httpx
import pytest

from civic_stack.app import app
from civic_stack.shared.http import UntrustedProxyError, browser_proxy_url, trusted_proxy_url
from civic_stack.shared.schema import not_found_response

ATTACKER_PROXY = "https://attacker.workers.dev"
PROXY_MODULES = ("ahu", "bpjph", "bpom", "ojk", "oss_nib")


@pytest.fixture(autouse=True)
def _clean_proxy_env(monkeypatch):
    for name in ("PROXY_URL", "PROXY_MODE", "CIVIC_ALLOWED_PROXIES"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def no_portal_calls(monkeypatch):
    """Fail closed: any scraper call reached through a router raises."""

    async def _portal_call(*args, **kwargs):
        raise AssertionError("portal call made with an untrusted proxy_url")

    for module in PROXY_MODULES:
        router = importlib.import_module(f"civic_stack.{module}.router")
        for name in ("fetch", "search", "check_waspada", "cross_ref_bpom"):
            if hasattr(router, name):
                monkeypatch.setattr(router, name, _portal_call)


def _proxy_operations():
    """Every REST operation accepting proxy_url, with dummy path and required query values."""
    for path, operations in app.openapi()["paths"].items():
        for method, operation in operations.items():
            params = operation.get("parameters", [])
            if not any(p["name"] == "proxy_url" for p in params):
                continue
            url, query = path, {"proxy_url": ATTACKER_PROXY}
            for p in params:
                if p["in"] == "path":
                    url = url.replace("{" + p["name"] + "}", "x")
                elif p.get("required"):
                    query[p["name"]] = "x"
            yield method.upper(), url, query


PROXY_OPERATIONS = list(_proxy_operations())


def test_untrusted_proxy_rejected():
    assert trusted_proxy_url(None) is None
    assert trusted_proxy_url("  ") is None
    with pytest.raises(UntrustedProxyError):
        trusted_proxy_url(ATTACKER_PROXY)


def test_operator_configured_proxies_accepted(monkeypatch):
    monkeypatch.setenv("PROXY_URL", "https://ours.workers.dev")
    monkeypatch.setenv(
        "CIVIC_ALLOWED_PROXIES", "socks5h://10.0.0.5:1080, http://user:pw@proxy.example:8080/"
    )
    assert trusted_proxy_url("https://ours.workers.dev/") == "https://ours.workers.dev/"
    assert trusted_proxy_url("socks5h://10.0.0.5:1080") == "socks5h://10.0.0.5:1080"
    assert trusted_proxy_url("http://user:pw@proxy.example:8080") == (
        "http://user:pw@proxy.example:8080"
    )
    for untrusted in (
        "socks5h://10.0.0.5:2222",
        "https://ours.workers.dev.attacker.example",
        ATTACKER_PROXY,
    ):
        with pytest.raises(UntrustedProxyError):
            trusted_proxy_url(untrusted)


def test_every_proxy_router_is_covered():
    assert len(PROXY_OPERATIONS) == 18
    assert {url.split("/")[1] for _, url, _ in PROXY_OPERATIONS} == {
        "ahu",
        "bpjph",
        "bpom",
        "ojk",
        "oss-nib",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(("method", "url", "query"), PROXY_OPERATIONS, ids=lambda v: str(v))
async def test_rest_rejects_untrusted_proxy(no_portal_calls, method, url, query):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.request(method, url, params=query)
    assert resp.status_code == 400
    assert "proxy_url" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_rest_forwards_configured_proxy(monkeypatch):
    monkeypatch.setenv("CIVIC_ALLOWED_PROXIES", "socks5h://10.0.0.5:1080")
    seen = []

    async def fake_check_waspada(q, *, proxy_url=None):
        seen.append(proxy_url)
        return not_found_response("ojk", "https://www.ojk.go.id")

    monkeypatch.setattr("civic_stack.ojk.router.check_waspada", fake_check_waspada)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        allowed = await client.get(
            "/ojk/waspada", params={"q": "x", "proxy_url": "socks5h://10.0.0.5:1080"}
        )
        default = await client.get("/ojk/waspada", params={"q": "x"})
    assert allowed.status_code == default.status_code == 200
    assert seen == ["socks5h://10.0.0.5:1080", None]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("module", "server_class", "tool", "arguments"),
    [
        ("ahu", "AhuMCPServer", "verify_company_status", {"company_id": "x"}),
        ("ahu", "AhuMCPServer", "search_companies_ahu", {"keyword": "x"}),
        ("oss_nib", "OssNibMCPServer", "verify_nib", {"nib_number": "x"}),
        ("oss_nib", "OssNibMCPServer", "search_oss_businesses", {"keyword": "x"}),
    ],
)
async def test_mcp_rejects_untrusted_proxy(monkeypatch, module, server_class, tool, arguments):
    server_module = importlib.import_module(f"civic_stack.{module}.server")

    async def _portal_call(*args, **kwargs):
        raise AssertionError("portal call made with an untrusted proxy_url")

    monkeypatch.setattr(server_module, "fetch", _portal_call)
    monkeypatch.setattr(server_module, "search", _portal_call)
    server = getattr(server_module, server_class)()
    result = await server.mcp.call_tool(tool, {**arguments, "proxy_url": ATTACKER_PROXY})
    payload = result.structured_content
    if isinstance(payload.get("result"), list):  # FastMCP wraps list returns
        payload = payload["result"][0]
    assert payload["status"] == "ERROR"
    assert "proxy_url" in payload["result"]["detail"]


def test_browser_proxy_falls_back_to_connect_env(monkeypatch):
    assert browser_proxy_url() is None
    assert browser_proxy_url("socks5://explicit:1080") == "socks5://explicit:1080"
    monkeypatch.setenv("PROXY_URL", "socks5h://127.0.0.1:1080")
    assert browser_proxy_url() == "socks5h://127.0.0.1:1080"
    monkeypatch.setenv("PROXY_URL", "https://ours.workers.dev")
    assert browser_proxy_url() is None
