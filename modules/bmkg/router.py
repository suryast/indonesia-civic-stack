"""FastAPI router for the BMKG module."""

from __future__ import annotations

from fastapi import APIRouter, Query

from shared.schema import CivicStackResponse

from .scraper import fetch, get_alerts, get_earthquake_history, get_latest_earthquake, get_weather_forecast

router = APIRouter(prefix="/bmkg", tags=["BMKG"])


@router.get(
    "/forecast/{city}",
    response_model=CivicStackResponse,
    summary="Get 3-day weather forecast for an Indonesian city",
)
async def weather_forecast(city: str) -> CivicStackResponse:
    return await get_weather_forecast(city)


@router.get(
    "/earthquake/latest",
    response_model=CivicStackResponse,
    summary="Get the most recent significant earthquake from BMKG",
)
async def latest_earthquake() -> CivicStackResponse:
    return await get_latest_earthquake()


@router.get(
    "/earthquake/history",
    response_model=list[CivicStackResponse],
    summary="Get recent earthquake history, optionally filtered by region",
)
async def earthquake_history(
    region: str = Query("", description="Region name filter (optional)"),
    days: int = Query(7, description="Number of days to look back"),
) -> list[CivicStackResponse]:
    return await get_earthquake_history(region, days=days)


@router.get(
    "/alerts",
    response_model=list[CivicStackResponse],
    summary="Get active BMKG weather and disaster alerts",
)
async def alerts(
    region: str = Query("", description="Region name filter (optional)"),
) -> list[CivicStackResponse]:
    return await get_alerts(region)
