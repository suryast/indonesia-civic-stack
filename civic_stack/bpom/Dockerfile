FROM python:3.11-slim

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata first for layer caching
COPY pyproject.toml .
COPY civic_stack/ ./civic_stack/

# Install runtime dependencies only (no dev extras)
RUN pip install --no-cache-dir httpx "beautifulsoup4>=4.12" fastapi uvicorn fastmcp pydantic

EXPOSE 8000

# Default: start the FastAPI server
CMD ["uvicorn", "civic_stack.bpom.app:app", "--host", "0.0.0.0", "--port", "8000"]
