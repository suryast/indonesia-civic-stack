"""FastAPI application entry point for the OJK module."""

from fastapi import FastAPI

from civic_stack.ojk.router import router

app = FastAPI(
    title="indonesia-civic-stack / ojk",
    description="OJK licensed institution registry — ojk.go.id",
    version="0.1.0",
)
app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "module": "ojk"}
