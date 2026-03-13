"""FastAPI application entry point for the BPJPH module."""

from fastapi import FastAPI

from modules.bpjph.router import router

app = FastAPI(
    title="indonesia-civic-stack / bpjph",
    description="BPJPH SiHalal certificate scraper — sertifikasi.halal.go.id",
    version="0.1.0",
)

app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "module": "bpjph"}
