FROM python:3.12-slim

WORKDIR /app

# Install system deps for playwright browsers
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install package with MCP deps
COPY . .
RUN pip install --no-cache-dir -e ".[mcp]"

# FastMCP settings - Railway provides PORT
ENV FASTMCP_HOST=0.0.0.0

# Run MCP server in HTTP mode - uses $PORT from Railway
CMD python -m civic_stack.server --transport http --host 0.0.0.0 --port ${PORT:-8000}
