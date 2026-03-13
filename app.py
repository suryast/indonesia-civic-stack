"""
Unified FastAPI application — mounts all module routers.

This is the single-process entry point for local development and Railway
deployment when running all modules together. In production, each module
can also be deployed independently via its own modules/<name>/app.py.

Usage:
    uvicorn app:app --reload
    uvicorn app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
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

# Phase 1 routers
app.include_router(bpom_router)
app.include_router(bpjph_router)
app.include_router(ahu_router)

# Phase 2 routers
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
