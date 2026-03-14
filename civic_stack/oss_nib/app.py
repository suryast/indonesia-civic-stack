"""FastAPI application entry point for the OSS-NIB module."""

from fastapi import FastAPI

from civic_stack.oss_nib.router import router

app = FastAPI(
    title="indonesia-civic-stack / oss-nib",
    description="OSS RBA NIB business identity scraper — oss.go.id",
    version="0.1.0",
)
app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "module": "oss-nib"}
