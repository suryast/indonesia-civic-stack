FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
COPY shared/ ./shared/
COPY modules/lpse/ ./modules/lpse/
COPY modules/__init__.py ./modules/__init__.py
RUN pip install --no-cache-dir httpx fastapi uvicorn fastmcp pydantic
EXPOSE 8000
CMD ["uvicorn", "modules.lpse.app:app", "--host", "0.0.0.0", "--port", "8000"]
