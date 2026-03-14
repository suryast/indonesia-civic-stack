"""Standalone FastAPI app for the LHKPN module."""

from __future__ import annotations

from fastapi import FastAPI

from .router import router

app = FastAPI(
    title="LHKPN — KPK Wealth Declarations",
    version="0.1.0",
    description="Search and extract Indonesian public official wealth declarations (LHKPN) from KPK.",
)

app.include_router(router)
