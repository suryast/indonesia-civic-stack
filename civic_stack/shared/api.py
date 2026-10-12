"""
Shared FastAPI helpers for module routers.

Kept separate from http.py so shared/ stays importable without the ``api`` extra.
"""

from __future__ import annotations

from fastapi import HTTPException, Query

from civic_stack.shared.http import UntrustedProxyError, trusted_proxy_url


def proxy_url_param(
    proxy_url: str | None = Query(
        None,
        description=(
            "Operator-configured proxy URL (must match PROXY_URL or an entry in "
            "CIVIC_ALLOWED_PROXIES). Omit to use the server's PROXY_URL."
        ),
    ),
) -> str | None:
    """FastAPI dependency: accept a caller-supplied proxy_url only if the operator trusts it."""
    try:
        return trusted_proxy_url(proxy_url)
    except UntrustedProxyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
