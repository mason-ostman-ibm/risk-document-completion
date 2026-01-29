# Quick Command Reference

## MCP Server

### Run Server
```bash
# Development mode with inspector UI
cd mcp_core
fastmcp dev mcp_server.py

# Production mode (stdio)
python mcp_core/mcp_server.py

# HTTP/SSE mode
python mcp_core/mcp_server.py --http --port 8000
```

### Test Server
```bash
python tests/test_running_server.py
python tests/demo_mcp_tools.py
```

## Orchestrate Tools

### Upload to Orchestrate
```bash
# Authenticate first
orchestrate env activate production

# Upload encoder
cd orchestrate_tools
orchestrate tools import --kind python \
  --file orchestrate_encode_file.py \
  --requirements-file orchestrate_tools_requirements.txt

# Upload decoder
orchestrate tools import --kind python \
  --file orchestrate_decode_file.py \
  --requirements-file orchestrate_tools_requirements.txt
```

### List Tools in Orchestrate
```bash
orchestrate tools list | grep -E "(encode_file_to_base64|decode_base64_to_file)"
```

### Test Tools Locally
```bash
python tests/test_decode.py
```

## Setup & Installation

### First Time Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r config/requirements.txt

# Configure environment
cp config/.env.example config/.env
# Edit .env with your credentials
```

### Activate Environment
```bash
source venv/bin/activate
```

## Git Commands

### Commit Changes
```bash
git add mcp_core/ orchestrate_tools/ docs/ config/
git commit -m "Organize project structure"
```

### Check Status
```bash
git status
git diff
```

## Docker (Optional)

### Build Image
```bash
docker build -f config/Dockerfile -t risk-document-completion .
```

### Run Container
```bash
docker run -p 8000:8000 --env-file config/.env risk-document-completion
```

## Common Tasks

### Update Orchestrate Tool
```bash
# 1. Edit tool in orchestrate_tools/
# 2. Re-authenticate if needed
orchestrate env activate production

# 3. Re-upload
cd orchestrate_tools
orchestrate tools import --kind python \
  --file <tool_name>.py \
  --requirements-file orchestrate_tools_requirements.txt
```

### Test Full Workflow
```bash
# 1. Start MCP server
python mcp_core/mcp_server.py &

# 2. Test in Orchestrate or use test scripts
python tests/test_running_server.py

# 3. Stop server
kill %1
```

### Check MCP Server Health
```bash
# List available MCP tools
python -c "from mcp_core.mcp_server import mcp; print([t for t in dir(mcp) if not t.startswith('_')])"
```

## Troubleshooting

### Orchestrate Token Expired
```bash
orchestrate env activate production
# Enter your WXO API key
```

### Python Dependencies Issue
```bash
pip install --upgrade -r config/requirements.txt
```

### Test Decoder Standalone
```bash
cd tests
python test_decode.py
```

### View Orchestrate Logs
```bash
orchestrate tools list
# Check for your tools and their status
```
