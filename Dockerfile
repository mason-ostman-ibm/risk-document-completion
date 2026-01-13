# Dockerfile for Risk Document Completion MCP Server
# Optimized for IBM Code Engine deployment

FROM python:3.11-slim

# Set metadata
LABEL maintainer="IBM Watson Orchestrate"
LABEL description="Risk Document Completion MCP Server for WatsonX Orchestrate"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY auto_complete_document.py .
COPY mcp_server.py .
COPY detect_qa_columns.py .

# Create directory for temporary files
RUN mkdir -p /tmp/document_completion && \
    chmod 777 /tmp/document_completion

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV TEMP_DIR=/tmp/document_completion

# Expose port for HTTP endpoint (Code Engine will map this)
EXPOSE 8080

# Health check (optional but recommended for Code Engine)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the MCP server
# Note: Environment variables (MODEL_URL, API_KEY, etc.) will be provided by Code Engine
CMD ["python", "-u", "mcp_server.py"]
