FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
COPY shared/ ./shared/
COPY modules/lhkpn/ ./modules/lhkpn/
COPY modules/__init__.py ./modules/__init__.py
# Base deps + optional PDF extras
RUN pip install --no-cache-dir httpx fastapi uvicorn fastmcp pydantic && \
    pip install --no-cache-dir pdfplumber anthropic || true
EXPOSE 8000
CMD ["uvicorn", "modules.lhkpn.app:app", "--host", "0.0.0.0", "--port", "8000"]
