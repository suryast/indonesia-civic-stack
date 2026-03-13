"""FastAPI application entry point for the KPU module."""

from fastapi import FastAPI
from modules.kpu.router import router

app = FastAPI(
    title="indonesia-civic-stack / kpu",
    description="KPU election data API wrapper — sirekap + infopemilu",
    version="0.1.0",
)
app.include_router(router)

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "module": "kpu"}
