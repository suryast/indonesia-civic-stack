"""Regression coverage for the packaged and repository REST entry points."""

import httpx
import pytest

from civic_stack import __version__
from civic_stack.app import app


def test_root_app_is_packaged_app():
    from app import app as repository_app

    assert repository_app is app


@pytest.mark.asyncio
async def test_public_metadata_and_openapi_use_release_version():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        root = (await client.get("/")).json()
        health = (await client.get("/health")).json()
        spec = (await client.get("/openapi.json")).json()
    assert root["version"] == spec["info"]["version"] == __version__
    assert root["modules"] == health["modules"]
    assert len(root["modules"]) == 11
    assert "/bpom/search" in spec["paths"]
