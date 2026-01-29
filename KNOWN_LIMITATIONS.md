# Known Limitations

## Port Configuration Issue

**Issue:** The MCP server runs on `127.0.0.1:8000` instead of the configured `0.0.0.0:8080`.

**Root Cause:** FastMCP library doesn't expose configuration options for the underlying uvicorn server. The `mcp.run(transport='sse')` method internally starts uvicorn with hardcoded defaults (host=127.0.0.1, port=8000).

**Attempted Solutions:**
1. ❌ Monkey-patching sys.argv - FastMCP doesn't pass arguments to uvicorn
2. ❌ Setting UVICORN_HOST/UVICORN_PORT environment variables - FastMCP doesn't read them
3. ❌ Direct uvicorn.run() call - Requires complex ASGI app reconstruction

**Workarounds:**

### Option 1: Port Forwarding (Recommended for Docker/Podman)
Map the container's internal port 8000 to external port 8080:
```bash
podman run -p 8080:8000 risk-document-mcp:latest
```

### Option 2: Reverse Proxy
Use nginx or another reverse proxy to forward requests from 8080 to 8000:
```nginx
server {
    listen 8080;
    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

### Option 3: Fork FastMCP
Create a custom version of FastMCP that exposes uvicorn configuration options.

## Impact

- Container health checks on port 8080 will fail
- External services expecting port 8080 need to use port 8000 instead
- The `--port` and `--host` CLI arguments are currently non-functional

## Future Resolution

This requires either:
1. Upstream fix in FastMCP library to expose uvicorn configuration
2. Switch to a different MCP server implementation that supports configuration
3. Implement custom ASGI server wrapper (complex, maintenance burden)