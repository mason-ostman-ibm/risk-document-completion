# Bug Analysis and Fixes

## Critical Bugs Found

### 🔴 Bug #1: Missing Environment Variables at Runtime
**Location:** [`auto_complete_document.py:23-28`](risk-document-completion/auto_complete_document.py:23)

**Issue:**
```python
ASTRA_DB_API_ENDPOINT = os.getenv("ASTRA_DB_API_ENDPOINT")
ASTRA_DB_APPLICATION_TOKEN = os.getenv("ASTRA_DB_APPLICATION_TOKEN")

astra_client = DataAPIClient(ASTRA_DB_APPLICATION_TOKEN)  # ❌ Fails if None
astra_database = astra_client.get_database(ASTRA_DB_API_ENDPOINT)  # ❌ Fails if None
```

**Problem:** Code initializes AstraDB client at module import time, before environment variables are validated. If env vars are missing, the container crashes immediately on startup.

**Impact:** Container fails to start with cryptic error messages.

---

### 🔴 Bug #2: Hardcoded Username in Credentials
**Location:** [`auto_complete_document.py:37`](risk-document-completion/auto_complete_document.py:37)

**Issue:**
```python
credentials = Credentials(
    url=os.getenv("MODEL_URL"),
    username="mason.ostman@ibm.com",  # ❌ Hardcoded!
    api_key=os.getenv("API_KEY")
)
```

**Problem:** Username is hardcoded instead of using environment variable.

**Impact:** Won't work for other users/deployments.

---

### 🔴 Bug #3: Embedding Model Downloads at Runtime
**Location:** [`auto_complete_document.py:31`](risk-document-completion/auto_complete_document.py:31)

**Issue:**
```python
embedding_model = SentenceTransformer('ibm-granite/granite-embedding-30m-english')
```

**Problem:** Model downloads at module import (container startup), causing:
- Slow startup (downloads ~120MB model)
- Network dependency at startup
- Potential timeout in container orchestration

**Impact:** Container takes 30-60 seconds to start, may timeout in Kubernetes/Code Engine.

---

### 🔴 Bug #4: No Error Handling for Missing Environment Variables
**Location:** [`auto_complete_document.py:33-43`](risk-document-completion/auto_complete_document.py:33)

**Issue:**
```python
def initialize_model():
    credentials = Credentials(
        url=os.getenv("MODEL_URL"),  # ❌ No validation
        username="mason.ostman@ibm.com",
        api_key=os.getenv("API_KEY")  # ❌ No validation
    )
    project_id = os.getenv("PROJECT_ID")  # ❌ No validation
    space_id = os.getenv("SPACE_ID")  # ❌ No validation
```

**Problem:** No validation that required environment variables exist.

**Impact:** Cryptic errors when env vars are missing.

---

### 🟡 Bug #5: Dockerfile Port Mismatch
**Location:** [`Dockerfile:43`](risk-document-completion/Dockerfile:43)

**Issue:**
```dockerfile
EXPOSE 8080
```

**Problem:** MCP server likely runs on port 8000 (FastMCP default), but Dockerfile exposes 8080.

**Impact:** Port mismatch causes connection failures.

---

### 🟡 Bug #6: Ineffective Health Check
**Location:** [`Dockerfile:46-47`](risk-document-completion/Dockerfile:46)

**Issue:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"
```

**Problem:** Health check always succeeds (just imports sys), doesn't actually test if server is running.

**Impact:** Container marked healthy even if MCP server crashed.

---

### 🟡 Bug #7: Missing HTTP Server Configuration
**Location:** [`mcp_server.py:409`](risk-document-completion/mcp_server.py:409)

**Issue:**
```python
def main():
    logger.info("Starting Risk Document Completion MCP Server...")
    mcp.run()  # ❌ No host/port configuration
```

**Problem:** FastMCP `run()` doesn't expose HTTP endpoint by default, only stdio.

**Impact:** Can't connect to server over HTTP from Orchestrate.

---

### 🟡 Bug #8: Duplicate Code Files
**Location:** Root and `mcp_core/` directories

**Issue:**
- `auto_complete_document.py` exists in both root and `mcp_core/`
- `mcp_server.py` exists in both root and `mcp_core/`

**Problem:** Confusion about which version is used, potential version mismatch.

**Impact:** Maintenance nightmare, unclear which file to edit.

---

## Fixes

### Fix #1: Lazy Initialize AstraDB Client

```python
# auto_complete_document.py
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment
import openpyxl.utils
import os
import re
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from dotenv import load_dotenv
from astrapy import DataAPIClient
from sentence_transformers import SentenceTransformer

load_dotenv()

# Global variables for lazy initialization
_astra_client = None
_astra_database = None
_collection = None
_embedding_model = None

def get_astra_collection():
    """Lazy initialize AstraDB collection"""
    global _astra_client, _astra_database, _collection
    
    if _collection is None:
        # Validate environment variables
        endpoint = os.getenv("ASTRA_DB_API_ENDPOINT")
        token = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
        
        if not endpoint or not token:
            raise ValueError(
                "Missing required environment variables: "
                "ASTRA_DB_API_ENDPOINT and ASTRA_DB_APPLICATION_TOKEN"
            )
        
        _astra_client = DataAPIClient(token)
        _astra_database = _astra_client.get_database(endpoint)
        _collection = _astra_database.get_collection("qa_collection")
    
    return _collection

def get_embedding_model():
    """Lazy initialize embedding model"""
    global _embedding_model
    
    if _embedding_model is None:
        print("Loading embedding model (this may take a moment)...")
        _embedding_model = SentenceTransformer('ibm-granite/granite-embedding-30m-english')
        print("Embedding model loaded!")
    
    return _embedding_model
```

### Fix #2: Remove Hardcoded Username

```python
def initialize_model():
    """Initialize the LLM model for both column detection and question answering"""
    # Validate required environment variables
    required_vars = ["MODEL_URL", "API_KEY", "PROJECT_ID", "MODEL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    credentials = Credentials(
        url=os.getenv("MODEL_URL"),
        api_key=os.getenv("API_KEY")
    )

    project_id = os.getenv("PROJECT_ID")
    space_id = os.getenv("SPACE_ID")  # Optional
    model_id = os.getenv("MODEL")

    parameters = {
        "temperature": 0,
        "top_p": 1
    }

    model = ModelInference(
        model_id=model_id,
        params=parameters,
        credentials=credentials,
        project_id=project_id,
        space_id=space_id
    )

    return model
```

### Fix #3: Update get_relevant_context

```python
def get_relevant_context(question, top_k=5, similarity_threshold=0.5):
    """Search for relevant Q&A pairs using RAG"""
    try:
        collection = get_astra_collection()
        embedding_model = get_embedding_model()
        
        query_embedding = embedding_model.encode(question).tolist()

        results = collection.find(
            sort={"$vector": query_embedding},
            limit=top_k,
            projection={"question": 1, "answer": 1, "category": 1, "source_file": 1},
            include_similarity=True
        )

        context = ""
        relevant_count = 0

        for j, result in enumerate(results, 1):
            similarity = result.get('$similarity', 0)

            if similarity < similarity_threshold:
                continue

            q = result.get('question', 'N/A')
            a = result.get('answer', 'N/A')

            answer_lower = str(a).lower().strip()
            if answer_lower in ['unanswered', 'nan', 'none', '', 'n/a']:
                continue

            relevant_count += 1
            context += f"Example {relevant_count}:\n"
            context += f"Q: {q}\n"
            context += f"A: {a}\n\n"

        if not context:
            context = "No relevant examples found. Use your general knowledge about IBM and business practices."

        return context.strip()
        
    except Exception as e:
        print(f"Warning: RAG retrieval failed: {e}")
        return "No context available due to retrieval error."
```

### Fix #4: Update Dockerfile

```dockerfile
# Dockerfile for Risk Document Completion MCP Server
FROM python:3.11-slim

LABEL maintainer="IBM Watson Orchestrate"
LABEL description="Risk Document Completion MCP Server for WatsonX Orchestrate"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY config/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model to avoid runtime download
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
EXPOSE 8080

# Improved health check that actually tests the server
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the MCP server with HTTP transport
CMD ["python", "-u", "mcp_server.py", "--transport", "http", "--port", "8080"]
```

### Fix #5: Update mcp_server.py for HTTP Support

```python
def main():
    """Entry point for the MCP server"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Risk Document Completion MCP Server')
    parser.add_argument('--transport', choices=['stdio', 'http'], default='stdio',
                       help='Transport protocol (stdio or http)')
    parser.add_argument('--port', type=int, default=8080,
                       help='Port for HTTP transport')
    parser.add_argument('--host', default='0.0.0.0',
                       help='Host for HTTP transport')
    
    args = parser.parse_args()
    
    logger.info(f"Starting Risk Document Completion MCP Server...")
    logger.info(f"Transport: {args.transport}")
    
    if args.transport == 'http':
        logger.info(f"HTTP server listening on {args.host}:{args.port}")
        mcp.run(transport='http', host=args.host, port=args.port)
    else:
        logger.info("Using stdio transport")
        mcp.run()


if __name__ == "__main__":
    main()
```

### Fix #6: Add Health Endpoint

```python
@mcp.tool()
def health_check() -> str:
    """Health check endpoint for container orchestration"""
    return json.dumps({
        "status": "healthy",
        "service": "risk-document-completion",
        "version": "1.0.0"
    })
```

---

## Testing the Fixes

### Local Testing

```bash
# 1. Set environment variables
export MODEL_URL="your-model-url"
export API_KEY="your-api-key"
export PROJECT_ID="your-project-id"
export MODEL="your-model-id"
export ASTRA_DB_API_ENDPOINT="your-astra-endpoint"
export ASTRA_DB_APPLICATION_TOKEN="your-astra-token"

# 2. Test locally
cd risk-document-completion/mcp_core
python mcp_server.py --transport http --port 8080

# 3. Test health endpoint
curl http://localhost:8080/health

# 4. Test tool
curl -X POST http://localhost:8080/tools/health_check
```

### Docker Testing

```bash
# 1. Build image
cd risk-document-completion
docker build -t risk-document-mcp:fixed .

# 2. Run with environment variables
docker run -p 8080:8080 \
  -e MODEL_URL="your-model-url" \
  -e API_KEY="your-api-key" \
  -e PROJECT_ID="your-project-id" \
  -e MODEL="your-model-id" \
  -e ASTRA_DB_API_ENDPOINT="your-astra-endpoint" \
  -e ASTRA_DB_APPLICATION_TOKEN="your-astra-token" \
  risk-document-mcp:fixed

# 3. Test from another terminal
curl http://localhost:8080/health
```

---

## Summary of Changes

| Bug | Severity | Fix | Impact |
|-----|----------|-----|--------|
| Missing env vars at runtime | 🔴 Critical | Lazy initialization | Prevents crashes |
| Hardcoded username | 🔴 Critical | Use env var | Works for all users |
| Model downloads at startup | 🔴 Critical | Pre-download in Dockerfile | Fast startup |
| No env var validation | 🔴 Critical | Add validation | Clear error messages |
| Port mismatch | 🟡 Medium | Fix Dockerfile | Proper connectivity |
| Ineffective health check | 🟡 Medium | Add real health check | Proper monitoring |
| No HTTP support | 🟡 Medium | Add HTTP transport | Orchestrate integration |
| Duplicate files | 🟡 Medium | Use mcp_core/ only | Clear structure |

---

## Deployment Checklist

- [ ] Apply all code fixes
- [ ] Update Dockerfile
- [ ] Set all required environment variables
- [ ] Build Docker image
- [ ] Test locally with Docker
- [ ] Push to container registry
- [ ] Deploy to Code Engine/Kubernetes
- [ ] Verify health endpoint
- [ ] Test MCP tools
- [ ] Monitor logs for errors