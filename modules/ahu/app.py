"""FastAPI application entry point for the AHU module."""

from fastapi import FastAPI

from modules.ahu.router import router

app = FastAPI(
    title="indonesia-civic-stack / ahu",
    description="AHU company registry scraper — ahu.go.id (Kemenkumham)",
    version="0.1.0",
)

app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "module": "ahu"}
