"""Standalone FastAPI app for the SIMBG module."""

from __future__ import annotations

from fastapi import FastAPI

from .router import router

app = FastAPI(
    title="SIMBG — Building Permit System",
    version="0.1.0",
    description=(
        "Building permit (PBG/IMB) lookup aggregated from SIMBG national API "
        "and 5 pilot regional portals (Jakarta, Surabaya, Bandung, Medan, Makassar)."
    ),
)

app.include_router(router)
