"""Standalone FastAPI app for the LPSE module."""

from __future__ import annotations

from fastapi import FastAPI

from .router import router

app = FastAPI(
    title="LPSE — Indonesia Government Procurement",
    version="0.1.0",
    description="Vendor and tender lookup across Indonesian LPSE portals (SPSE v4).",
)

app.include_router(router)
