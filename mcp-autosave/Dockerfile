# ============================================================================
# Synapse Layer — Auto-Save MCP Bridge: Docker Image
# ============================================================================
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .
COPY redactor.py .

# Security: run as non-root
RUN useradd -m synapse
USER synapse

# MCP servers use stdio transport — no port needed
ENTRYPOINT ["python", "server.py"]
