# CLAUDE.md - Risk Document Completion Project

This file provides guidance to Claude Code when working with this repository.

## Project Structure

```
risk-document-completion/
├── mcp_core/                      # MCP Server Core Files
│   ├── mcp_server.py             # FastMCP server with 6 tools
│   └── auto_complete_document.py # RAG document completion logic
│
├── orchestrate_tools/             # WatsonX Orchestrate Python Tools
│   ├── orchestrate_encode_file.py           # Encoder (file bytes → base64)
│   ├── orchestrate_decode_file.py           # Decoder (base64 → file bytes)
│   ├── orchestrate_decode_file_with_message.py  # Alternative decoder
│   └── orchestrate_tools_requirements.txt   # Tool dependencies
│
├── config/                        # Configuration Files
│   ├── requirements.txt          # MCP server dependencies
│   ├── Dockerfile               # Container deployment config
│   └── .env                     # Environment variables (not in git)
│
├── tests/                         # Testing & Demo Files
│   ├── test_decode.py           # Test decoder tool
│   ├── test_running_server.py   # Test MCP server
│   ├── demo_mcp_tools.py        # Demo MCP tool usage
│   ├── decode_string.txt        # Sample base64 input
│   ├── decoded_output.xlsx      # Test output
│   └── test*.xlsx               # Test Excel files
│
├── docs/                          # Documentation
│   ├── CLAUDE.md                # Original detailed guide
│   ├── ORCHESTRATE_WORKFLOW.md  # Orchestrate integration guide
│   └── README.md                # Project overview
│
└── venv/                          # Python virtual environment

```

## Quick Start

### MCP Server (Core Functionality)
```bash
# Install dependencies
pip install -r config/requirements.txt

# Run MCP server
python mcp_core/mcp_server.py
```

### Orchestrate Tools (Upload to Orchestrate)
```bash
# Authenticate
orchestrate env activate production

# Upload encoder tool
cd orchestrate_tools
orchestrate tools import --kind python --file orchestrate_encode_file.py --requirements-file orchestrate_tools_requirements.txt

# Upload decoder tool
orchestrate tools import --kind python --file orchestrate_decode_file.py --requirements-file orchestrate_tools_requirements.txt
```

## Key Components

### MCP Server Core (`mcp_core/`)

**mcp_server.py** - Main MCP server exposing 6 tools:
1. `complete_risk_document` - File path based processing
2. `complete_risk_document_from_bytes` - Bytes based processing
3. `complete_risk_document_base64` - Base64 workflow (for Orchestrate)
4. `detect_qa_columns` - LLM-based column detection
5. `answer_single_question` - Single Q&A with RAG
6. `search_knowledge_base` - AstraDB vector search
7. `list_excel_sheets` - List workbook sheets

**auto_complete_document.py** - RAG implementation:
- IBM WatsonX AI integration (Mistral-Small or Llama)
- AstraDB vector database queries
- Excel document processing with openpyxl
- LLM-based Q&A column detection

### Orchestrate Tools (`orchestrate_tools/`)

**orchestrate_encode_file.py**
- Input: `file_bytes` (from Orchestrate upload), `filename`
- Output: Base64 string
- Purpose: Convert uploaded files to base64 for MCP tool

**orchestrate_decode_file.py**
- Input: `file_base64` (from MCP tool output)
- Output: File bytes (Orchestrate provides download link)
- Purpose: Convert base64 back to downloadable file

## Complete Orchestrate Workflow

```
1. User uploads Excel file in Orchestrate
   ↓
2. encode_file_to_base64(file_bytes, filename)
   → Returns: "UEsDBBQ..." (base64 string)
   ↓
3. complete_risk_document_base64(base64_string, filename)
   → Returns: JSON {"success": true, "file_base64": "...", ...}
   ↓
4. Extract JSON field: result.file_base64
   ↓
5. decode_base64_to_file(extracted_base64)
   → Returns: bytes (Orchestrate provides S3 download link)
   ↓
6. User downloads completed file
```

## Environment Variables

Required in `config/.env`:
```bash
# IBM WatsonX
PROJECT_ID=...
API_KEY=...
MODEL_URL=https://...
MODEL=mistralai/mistral-small-3-1-24b-instruct-2503

# AstraDB
ASTRA_DB_API_ENDPOINT=https://...
ASTRA_DB_APPLICATION_TOKEN=AstraCS:...
```

## Development Workflow

### Testing MCP Server Locally
```bash
# Run FastMCP inspector UI
cd mcp_core
fastmcp dev mcp_server.py

# Or test directly
python tests/test_running_server.py
```

### Testing Orchestrate Tools
```bash
# Test decoder locally
python tests/test_decode.py
```

### Updating Orchestrate Tools
After modifying tools in `orchestrate_tools/`:
1. Re-authenticate: `orchestrate env activate production`
2. Re-upload: `orchestrate tools import --kind python --file <tool>.py --requirements-file orchestrate_tools_requirements.txt`

## Key Differences: MCP Tools vs Orchestrate Tools

| Aspect | MCP Tools | Orchestrate Tools |
|--------|-----------|-------------------|
| Location | `mcp_core/` | `orchestrate_tools/` |
| Purpose | RAG document processing | Base64 encoding/decoding |
| Dependencies | WatsonX AI, AstraDB, openpyxl | Python stdlib only |
| Decorator | `@mcp.tool()` | `@tool()` from orchestrate SDK |
| Input/Output | Files, bytes, base64, JSON | bytes ↔ base64 conversion |

## Important Notes

- **MCP server must be running** and accessible for Orchestrate workflow to work
- **Orchestrate tools run IN Orchestrate**, not in MCP server
- **File uploads in Orchestrate** are passed as bytes, not file paths
- **MCP tool returns JSON** with `file_base64` field that must be extracted

## Documentation

- Full development guide: `docs/CLAUDE.md`
- Orchestrate integration: `docs/ORCHESTRATE_WORKFLOW.md`
- Project overview: `docs/README.md`

## Git Status

Modified files: `mcp_core/mcp_server.py`
Untracked: Test files, Orchestrate tools, documentation
