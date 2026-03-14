"""FastAPI application entry point for the BPOM module."""

from fastapi import FastAPI

from civic_stack.bpom.router import router

app = FastAPI(
    title="indonesia-civic-stack / bpom",
    description="BPOM product registry scraper — cekbpom.pom.go.id",
    version="0.1.0",
)

app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "module": "bpom"}
