"""Standalone FastAPI app for the BPS module."""

from __future__ import annotations

from fastapi import FastAPI

from .router import router

app = FastAPI(
    title="BPS — Statistics Indonesia",
    version="0.1.0",
    description="Search and retrieve official statistical data from BPS (webapi.bps.go.id).",
)

app.include_router(router)
