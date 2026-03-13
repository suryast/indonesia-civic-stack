"""Standalone FastAPI app for the BMKG module."""

from __future__ import annotations

from fastapi import FastAPI

from .router import router

app = FastAPI(
    title="BMKG — Indonesian Meteorological Agency",
    version="0.1.0",
    description="Weather forecasts, earthquake data, and disaster alerts from BMKG.",
)

app.include_router(router)
