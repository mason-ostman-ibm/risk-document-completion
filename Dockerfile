# Dockerfile for Risk Document Completion MCP Server
# Optimized for IBM Code Engine deployment

FROM python:3.11-slim

# Set metadata
LABEL maintainer="IBM Watson Orchestrate"
LABEL description="Risk Document Completion MCP Server for WatsonX Orchestrate"

# Set working directory
WORKDIR /app

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY config/requirements.txt .

# Install Python dependencies
# IMPORTANT: Install CPU-only PyTorch first to avoid 3.7GB of unnecessary CUDA libraries
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model to avoid runtime download (speeds up startup)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('ibm-granite/granite-embedding-30m-english')"

# Copy application files from mcp_core directory
COPY mcp_core/auto_complete_document.py .
COPY mcp_core/mcp_server.py .

# Create directory for temporary files
RUN mkdir -p /tmp/document_completion && \
    chmod 777 /tmp/document_completion

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV TEMP_DIR=/tmp/document_completion
ENV MCP_SERVER_PORT=8080

# Expose port for HTTP endpoint
# Note: FastMCP runs on port 8000 internally due to library limitations
# Use port mapping (e.g., -p 8080:8000) when running the container
EXPOSE 8000

# Improved health check with longer start period for model loading
# Check internal port 8000 where FastMCP actually runs
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the MCP server with HTTP transport
# Note: --port and --host arguments are non-functional due to FastMCP limitations
# Server will run on 127.0.0.1:8000 regardless. See KNOWN_LIMITATIONS.md
CMD ["python", "-u", "mcp_server.py", "--transport", "http"]
