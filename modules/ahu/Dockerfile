FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY shared/ ./shared/
COPY modules/ahu/ ./modules/ahu/
COPY modules/__init__.py ./modules/__init__.py

RUN pip install --no-cache-dir httpx "beautifulsoup4>=4.12" playwright fastapi uvicorn fastmcp pydantic

RUN playwright install chromium

# PROXY_URL must be set at runtime to a Cloudflare Worker or residential proxy.
# AHU will block requests without proxy routing from datacenter IPs.
ENV PROXY_URL=""

RUN useradd -m -u 1000 civicapp
USER civicapp
EXPOSE 8000

CMD ["uvicorn", "modules.ahu.app:app", "--host", "0.0.0.0", "--port", "8000"]
