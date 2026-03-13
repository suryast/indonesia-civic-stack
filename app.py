"""
Unified FastAPI application — mounts all module routers.

Security:
- API key authentication (set CIVIC_API_KEY env var to enable)
- Per-IP rate limiting (60 req/min default, configurable via CIVIC_RATE_LIMIT)

Usage:
    uvicorn app:app --reload
    uvicorn app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import os
import time
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from modules.ahu.router import router as ahu_router
from modules.bpjph.router import router as bpjph_router
from modules.bpom.router import router as bpom_router
from modules.kpu.router import router as kpu_router
from modules.lpse.router import router as lpse_router
from modules.ojk.router import router as ojk_router
from modules.oss_nib.router import router as oss_nib_router

app = FastAPI(
    title="indonesia-civic-stack",
    description=(
        "Production-ready scrapers and API wrappers for Indonesian government data sources. "
        "Phase 1: BPOM, BPJPH, AHU. Phase 2: KPU, OJK, OSS-NIB, LPSE."
    ),
    version="0.2.0",
    contact={
        "name": "indonesia-civic-stack contributors",
        "url": "https://github.com/suryast/indonesia-civic-stack",
    },
    license_info={
        "name": "MIT / Apache-2.0 (per module — see LICENSES.md)",
        "url": "https://github.com/suryast/indonesia-civic-stack/blob/main/LICENSES.md",
    },
)

# ---------------------------------------------------------------------------
# Rate limiting (in-memory, per-IP)
# ---------------------------------------------------------------------------
_RATE_LIMIT = int(os.environ.get("CIVIC_RATE_LIMIT", "60"))  # requests per minute
_rate_store: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(ip: str) -> bool:
    """Return True if request is within rate limit."""
    now = time.monotonic()
    window = 60.0
    timestamps = _rate_store[ip]
    # Prune old entries
    _rate_store[ip] = [t for t in timestamps if now - t < window]
    if len(_rate_store[ip]) >= _RATE_LIMIT:
        return False
    _rate_store[ip].append(now)
    return True


# ---------------------------------------------------------------------------
# Middleware: API key auth + rate limiting
# ---------------------------------------------------------------------------
_API_KEY = os.environ.get("CIVIC_API_KEY", "").strip()
_PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def auth_and_rate_limit(request: Request, call_next):
    path = request.url.path

    # API key check (only enforced if CIVIC_API_KEY is set)
    if path not in _PUBLIC_PATHS and _API_KEY:
        provided = request.headers.get("X-API-Key") or request.query_params.get("api_key") or ""
        if provided != _API_KEY:
            return JSONResponse(
                {"error": "Invalid or missing API key"},
                status_code=401,
                headers={"WWW-Authenticate": "ApiKey"},
            )

    # Rate limiting (always active)
    client_ip = request.headers.get(
        "X-Forwarded-For", request.client.host if request.client else "unknown"
    )
    if isinstance(client_ip, str) and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    if not _check_rate_limit(client_ip):
        return JSONResponse(
            {"error": "Rate limit exceeded", "limit": f"{_RATE_LIMIT}/min"},
            status_code=429,
            headers={"Retry-After": "60"},
        )

    return await call_next(request)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
# Phase 1
app.include_router(bpom_router)
app.include_router(bpjph_router)
app.include_router(ahu_router)

# Phase 2
app.include_router(kpu_router)
app.include_router(ojk_router)
app.include_router(oss_nib_router)
app.include_router(lpse_router)

_ALL_MODULES = ["bpom", "bpjph", "ahu", "kpu", "ojk", "oss_nib", "lpse"]


@app.get("/", include_in_schema=False)
async def root() -> JSONResponse:
    return JSONResponse(
        {
            "name": "indonesia-civic-stack",
            "version": "0.2.0",
            "phase": 2,
            "modules": _ALL_MODULES,
            "docs": "/docs",
            "openapi": "/openapi.json",
        }
    )


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "modules": _ALL_MODULES,
    }
