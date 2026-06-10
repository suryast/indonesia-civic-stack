FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
COPY civic_stack/ ./civic_stack/
RUN pip install --no-cache-dir httpx fastapi uvicorn fastmcp pydantic
EXPOSE 8000
CMD ["uvicorn", "civic_stack.simbg.app:app", "--host", "0.0.0.0", "--port", "8000"]
