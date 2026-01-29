# Risk Document Completion Tool

Auto-complete governance, compliance, and risk questionnaires using RAG (Retrieval-Augmented Generation).

## Overview

This project provides:
- **MCP Server**: FastMCP server with RAG-powered document completion
- **Orchestrate Tools**: Python tools for WatsonX Orchestrate integration
- **Base64 Workflow**: Complete file upload/download workflow for Orchestrate

## Quick Links

- **Full Guide**: [`CLAUDE.md`](CLAUDE.md) - Complete development documentation
- **Orchestrate Integration**: [`docs/ORCHESTRATE_WORKFLOW.md`](docs/ORCHESTRATE_WORKFLOW.md)
- **Original Docs**: [`docs/CLAUDE.md`](docs/CLAUDE.md)

## Project Structure

```
├── mcp_core/              # MCP server & RAG logic
├── orchestrate_tools/     # Python tools for Orchestrate
├── config/                # Configuration & dependencies
├── tests/                 # Testing & demo scripts
└── docs/                  # Documentation
```

## Setup

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r config/requirements.txt

# 3. Configure environment
cp config/.env.example config/.env
# Edit config/.env with your credentials

# 4. Run MCP server
python mcp_core/mcp_server.py
```

## Usage

### Local Development
```bash
# Run MCP server with FastMCP inspector
cd mcp_core
fastmcp dev mcp_server.py
```

### Orchestrate Deployment
```bash
# 1. Authenticate
orchestrate env activate production

# 2. Upload tools
cd orchestrate_tools
orchestrate tools import --kind python --file orchestrate_encode_file.py --requirements-file orchestrate_tools_requirements.txt
orchestrate tools import --kind python --file orchestrate_decode_file.py --requirements-file orchestrate_tools_requirements.txt
```

## Workflow

```
User Upload → Encode (base64) → MCP Process → Decode → Download
```

See [`docs/ORCHESTRATE_WORKFLOW.md`](docs/ORCHESTRATE_WORKFLOW.md) for details.

## Technologies

- **IBM WatsonX AI**: LLM for Q&A generation
- **AstraDB**: Vector database for RAG
- **FastMCP**: MCP protocol server
- **OpenPyXL**: Excel processing
- **WatsonX Orchestrate**: Agentic workflow platform

## License

MIT
