"""
Unified FastAPI application — mounts all Phase 1 module routers.

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

app = FastAPI(
    title="indonesia-civic-stack",
    description=(
        "Production-ready scrapers and API wrappers for Indonesian government data sources. "
        "Phase 1: BPOM product registry, BPJPH halal certificates, AHU company registry."
    ),
    version="0.1.0",
    contact={
        "name": "indonesia-civic-stack contributors",
        "url": "https://github.com/suryast/indonesia-civic-stack",
    },
    license_info={
        "name": "MIT / Apache-2.0 (per module — see LICENSES.md)",
        "url": "https://github.com/suryast/indonesia-civic-stack/blob/main/LICENSES.md",
    },
)

# Mount module routers
app.include_router(bpom_router)
app.include_router(bpjph_router)
app.include_router(ahu_router)


@app.get("/", include_in_schema=False)
async def root() -> JSONResponse:
    return JSONResponse(
        {
            "name": "indonesia-civic-stack",
            "version": "0.1.0",
            "phase": 1,
            "modules": ["bpom", "bpjph", "ahu"],
            "docs": "/docs",
            "openapi": "/openapi.json",
        }
    )


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "modules": ["bpom", "bpjph", "ahu"],
    }
