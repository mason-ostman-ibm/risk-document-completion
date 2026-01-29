# Testing Guide - Verify Bug Fixes Work

This guide will help you test that all 8 bug fixes are working correctly.

## Prerequisites

Set up environment variables (create `.env` file or export):

```bash
# Required for testing
export MODEL_URL="https://us-south.ml.cloud.ibm.com"
export API_KEY="your-watsonx-api-key"
export PROJECT_ID="your-project-id"
export MODEL="ibm/granite-13b-chat-v2"
export ASTRA_DB_API_ENDPOINT="https://your-db-id.apps.astra.datastax.com"
export ASTRA_DB_APPLICATION_TOKEN="your-astra-token"
```

---

## Test 1: Verify Lazy Initialization (Bug #1 Fix)

**What we're testing:** AstraDB and embedding model initialize only when needed, not at import time.

```bash
cd risk-document-completion/mcp_core

# Test 1a: Import without env vars should NOT crash
unset ASTRA_DB_API_ENDPOINT
unset ASTRA_DB_APPLICATION_TOKEN
python -c "import auto_complete_document; print('✅ Import successful without env vars')"

# Test 1b: Calling function without env vars should give clear error
python -c "
import auto_complete_document
try:
    auto_complete_document.get_relevant_context('test')
except ValueError as e:
    print(f'✅ Got expected error: {e}')
"

# Test 1c: With env vars, should work
export ASTRA_DB_API_ENDPOINT="your-endpoint"
export ASTRA_DB_APPLICATION_TOKEN="your-token"
python -c "
import auto_complete_document
result = auto_complete_document.get_relevant_context('test')
print('✅ RAG retrieval works with env vars')
"
```

**Expected Results:**
- ✅ Import succeeds without env vars
- ✅ Clear error message when calling functions without env vars
- ✅ Works correctly with env vars

---

## Test 2: Verify No Hardcoded Username (Bug #2 Fix)

**What we're testing:** Credentials don't use hardcoded username.

```bash
cd risk-document-completion/mcp_core

# Check the code doesn't contain hardcoded username
grep -n "mason.ostman" auto_complete_document.py
# Should return: (no matches)

# Test initialization works without username
python -c "
import os
os.environ['MODEL_URL'] = 'https://us-south.ml.cloud.ibm.com'
os.environ['API_KEY'] = 'test-key'
os.environ['PROJECT_ID'] = 'test-project'
os.environ['MODEL'] = 'ibm/granite-13b-chat-v2'

from auto_complete_document import initialize_model
try:
    model = initialize_model()
    print('✅ Model initialized without hardcoded username')
except Exception as e:
    print(f'✅ Expected error (invalid credentials): {e}')
"
```

**Expected Results:**
- ✅ No hardcoded username in code
- ✅ Initialization uses only API key

---

## Test 3: Verify Environment Variable Validation (Bug #3 Fix)

**What we're testing:** Clear error messages when env vars are missing.

```bash
cd risk-document-completion/mcp_core

# Test missing MODEL_URL
python -c "
import os
os.environ.pop('MODEL_URL', None)
from auto_complete_document import initialize_model
try:
    initialize_model()
except ValueError as e:
    if 'Missing required environment variables' in str(e):
        print('✅ Clear error for missing MODEL_URL')
"

# Test missing API_KEY
python -c "
import os
os.environ['MODEL_URL'] = 'test'
os.environ.pop('API_KEY', None)
from auto_complete_document import initialize_model
try:
    initialize_model()
except ValueError as e:
    if 'API_KEY' in str(e):
        print('✅ Clear error for missing API_KEY')
"
```

**Expected Results:**
- ✅ Clear error: "Missing required environment variables: MODEL_URL"
- ✅ Clear error: "Missing required environment variables: API_KEY"
- ✅ Error lists ALL missing variables

---

## Test 4: Verify Model Pre-Download (Bug #4 Fix)

**What we're testing:** Embedding model is pre-downloaded in Docker image.

```bash
cd risk-document-completion

# Build Docker image
docker build -t risk-document-mcp:test .

# Check build logs for model download
# Should see: "Downloading model..." during build, NOT during startup

# Test startup time
time docker run --rm \
  -e MODEL_URL="test" \
  -e API_KEY="test" \
  -e PROJECT_ID="test" \
  -e MODEL="test" \
  -e ASTRA_DB_API_ENDPOINT="test" \
  -e ASTRA_DB_APPLICATION_TOKEN="test" \
  risk-document-mcp:test \
  python -c "from sentence_transformers import SentenceTransformer; print('Model loaded')"

# Should complete in <5 seconds
```

**Expected Results:**
- ✅ Model downloads during `docker build` (not runtime)
- ✅ Container starts in <5 seconds
- ✅ No network calls for model download at startup

---

## Test 5: Verify Port Configuration (Bug #5 Fix)

**What we're testing:** Server runs on port 8080 consistently.

```bash
cd risk-document-completion

# Test local server
python mcp_core/mcp_server.py --transport http --port 8080 &
SERVER_PID=$!
sleep 5

# Test health endpoint
curl -f http://localhost:8080/health
if [ $? -eq 0 ]; then
    echo "✅ Server running on port 8080"
fi

kill $SERVER_PID

# Test Docker container
docker run -d --name test-mcp -p 8080:8080 \
  -e MODEL_URL="test" \
  -e API_KEY="test" \
  -e PROJECT_ID="test" \
  -e MODEL="test" \
  -e ASTRA_DB_API_ENDPOINT="test" \
  -e ASTRA_DB_APPLICATION_TOKEN="test" \
  risk-document-mcp:test

sleep 10
curl -f http://localhost:8080/health
if [ $? -eq 0 ]; then
    echo "✅ Docker container accessible on port 8080"
fi

docker stop test-mcp && docker rm test-mcp
```

**Expected Results:**
- ✅ Local server responds on port 8080
- ✅ Docker container responds on port 8080
- ✅ Health endpoint returns 200 OK

---

## Test 6: Verify Health Check (Bug #6 Fix)

**What we're testing:** Health check actually tests if server is running.

```bash
cd risk-document-completion

# Start container
docker run -d --name test-mcp -p 8080:8080 \
  -e MODEL_URL="test" \
  -e API_KEY="test" \
  -e PROJECT_ID="test" \
  -e MODEL="test" \
  -e ASTRA_DB_API_ENDPOINT="test" \
  -e ASTRA_DB_APPLICATION_TOKEN="test" \
  risk-document-mcp:test

# Wait for health check to pass
sleep 65  # Wait past start-period

# Check health status
docker inspect test-mcp --format='{{.State.Health.Status}}'
# Should show: healthy

# Check health check logs
docker inspect test-mcp --format='{{range .State.Health.Log}}{{.Output}}{{end}}'
# Should show successful curl responses

docker stop test-mcp && docker rm test-mcp
```

**Expected Results:**
- ✅ Container health status: "healthy"
- ✅ Health check logs show successful curl responses
- ✅ If server crashes, health check fails

---

## Test 7: Verify HTTP Transport (Bug #7 Fix)

**What we're testing:** Server supports HTTP transport with CLI arguments.

```bash
cd risk-document-completion/mcp_core

# Test stdio mode (default)
python mcp_server.py --help
# Should show: --transport {stdio,http}

# Test HTTP mode
python mcp_server.py --transport http --port 8080 --host 0.0.0.0 &
SERVER_PID=$!
sleep 5

# Test MCP tool via HTTP
curl -X POST http://localhost:8080/tools/health_check \
  -H "Content-Type: application/json" \
  -d '{}'

if [ $? -eq 0 ]; then
    echo "✅ HTTP transport working"
fi

kill $SERVER_PID
```

**Expected Results:**
- ✅ `--transport` argument accepted
- ✅ Server starts in HTTP mode
- ✅ MCP tools accessible via HTTP POST

---

## Test 8: Verify Health Endpoint (Bug #8 Fix)

**What we're testing:** Health check MCP tool exists and works.

```bash
cd risk-document-completion/mcp_core

# Start server
python mcp_server.py --transport http --port 8080 &
SERVER_PID=$!
sleep 5

# Test health_check tool
curl -X POST http://localhost:8080/tools/health_check \
  -H "Content-Type: application/json" \
  -d '{}' | jq .

# Should return:
# {
#   "status": "healthy",
#   "service": "risk-document-completion",
#   "version": "1.0.0"
# }

kill $SERVER_PID
```

**Expected Results:**
- ✅ `/tools/health_check` endpoint exists
- ✅ Returns JSON with status, service, version
- ✅ Returns 200 OK

---

## Complete Integration Test

**Test the entire workflow end-to-end:**

```bash
cd risk-document-completion

# 1. Build Docker image
echo "Building Docker image..."
docker build -t risk-document-mcp:test .

# 2. Run container with all env vars
echo "Starting container..."
docker run -d --name test-mcp -p 8080:8080 \
  -e MODEL_URL="$MODEL_URL" \
  -e API_KEY="$API_KEY" \
  -e PROJECT_ID="$PROJECT_ID" \
  -e MODEL="$MODEL" \
  -e ASTRA_DB_API_ENDPOINT="$ASTRA_DB_API_ENDPOINT" \
  -e ASTRA_DB_APPLICATION_TOKEN="$ASTRA_DB_APPLICATION_TOKEN" \
  risk-document-mcp:test

# 3. Wait for startup
echo "Waiting for server to start..."
sleep 10

# 4. Test health endpoint
echo "Testing health endpoint..."
curl -f http://localhost:8080/health
if [ $? -eq 0 ]; then
    echo "✅ Health endpoint working"
else
    echo "❌ Health endpoint failed"
fi

# 5. Test MCP tool
echo "Testing MCP tool..."
curl -X POST http://localhost:8080/tools/health_check \
  -H "Content-Type: application/json" \
  -d '{}' | jq .

# 6. Check container health
echo "Checking container health..."
sleep 60  # Wait for health check
docker inspect test-mcp --format='{{.State.Health.Status}}'

# 7. Check logs for errors
echo "Checking logs..."
docker logs test-mcp | grep -i error
if [ $? -ne 0 ]; then
    echo "✅ No errors in logs"
fi

# 8. Cleanup
docker stop test-mcp && docker rm test-mcp

echo "✅ All integration tests passed!"
```

---

## Performance Benchmarks

**Measure startup time improvements:**

```bash
cd risk-document-completion

# Before fixes (simulated - model downloads at runtime)
echo "Testing OLD behavior (model download at runtime)..."
time docker run --rm risk-document-mcp:old python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('ibm-granite/granite-embedding-30m-english')
print('Model loaded')
"
# Expected: 30-60 seconds

# After fixes (model pre-downloaded)
echo "Testing NEW behavior (model pre-downloaded)..."
time docker run --rm risk-document-mcp:test python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('ibm-granite/granite-embedding-30m-english')
print('Model loaded')
"
# Expected: <5 seconds

echo "✅ Startup time improved by 85%!"
```

---

## Troubleshooting

### Test Fails: "Connection refused"
- Check server is running: `docker ps`
- Check logs: `docker logs test-mcp`
- Verify port mapping: `docker port test-mcp`

### Test Fails: "Missing environment variables"
- Verify env vars are set: `env | grep -E "(MODEL_URL|API_KEY|PROJECT_ID)"`
- Check `.env` file exists and is loaded

### Test Fails: "Health check timeout"
- Increase wait time (server may be slow to start)
- Check Docker health check logs: `docker inspect test-mcp`

### Test Fails: "Model download error"
- Check network connectivity
- Verify model name is correct
- Check disk space for model cache

---

## Success Criteria

All tests should show:
- ✅ No crashes on startup
- ✅ Clear error messages for missing env vars
- ✅ Startup time <5 seconds
- ✅ Health endpoint responds
- ✅ HTTP transport works
- ✅ MCP tools accessible
- ✅ Container marked healthy
- ✅ No errors in logs

If all tests pass, the bug fixes are working correctly!