FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
COPY shared/ ./shared/
COPY modules/oss-nib/ ./modules/oss-nib/
COPY modules/oss_nib/ ./modules/oss_nib/
COPY modules/bpjph/browser.py ./modules/bpjph/browser.py
COPY modules/bpjph/__init__.py ./modules/bpjph/__init__.py
COPY modules/__init__.py ./modules/__init__.py
RUN pip install --no-cache-dir httpx fastapi uvicorn fastmcp pydantic playwright camoufox
RUN playwright install chromium --with-deps
RUN useradd -m -u 1000 civicapp
USER civicapp
EXPOSE 8000
CMD ["uvicorn", "modules.oss_nib.app:app", "--host", "0.0.0.0", "--port", "8000"]
