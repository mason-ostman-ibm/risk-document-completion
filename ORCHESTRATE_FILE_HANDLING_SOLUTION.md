# Watson Orchestrate File Handling Solution

## Problem Statement

The MCP server has a [`complete_risk_document_base64()`](risk-document-completion/mcp_core/mcp_server.py:318) tool that expects a base64-encoded file string, but when a user uploads a file in Watson Orchestrate chat, the file is stored in the chat history and needs to be extracted and converted to base64 before being passed to the MCP tool.

## Current Architecture

```
User Upload → Orchestrate Chat History → ??? → MCP Tool (expects base64)
```

## Solution: Three-Tool Workflow

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATE WORKFLOW                         │
└─────────────────────────────────────────────────────────────────┘

1. User uploads Excel file in chat
         ↓
2. Orchestrate stores file in chat history
         ↓
3. Python Tool: encode_file_to_base64
   - Input: file_bytes (from Orchestrate file reference)
   - Output: base64 string
         ↓
4. MCP Tool: complete_risk_document_base64
   - Input: base64 string + filename
   - Output: JSON with completed file as base64
         ↓
5. Python Tool: decode_base64_to_file
   - Input: base64 string from MCP output
   - Output: bytes for download
         ↓
6. User downloads completed file
```

## Implementation Details

### Tool 1: File Encoder (Python Tool)

**File:** [`orchestrate_tools/orchestrate_encode_file.py`](risk-document-completion/orchestrate_tools/orchestrate_encode_file.py:1)

**Purpose:** Extract file from Orchestrate chat history and convert to base64

**Key Points:**
- Receives `file_bytes` parameter - Orchestrate automatically extracts this from uploaded files
- Returns plain base64 string (not JSON) for easy chaining
- Validates file extension (.xlsx)

**Orchestrate Tool Definition:**
```python
@tool()
def encode_file_to_base64(file_bytes: bytes, filename: str = "document.xlsx") -> str:
    """Encode an Excel file to base64 string for MCP tool processing."""
    # Validate and encode
    file_base64 = base64.b64encode(file_bytes).decode('utf-8')
    return file_base64
```

### Tool 2: Document Processor (MCP Tool)

**File:** [`mcp_core/mcp_server.py`](risk-document-completion/mcp_core/mcp_server.py:318)

**Purpose:** Process Excel document with RAG and return completed file

**Key Points:**
- Accepts base64 string input
- Returns JSON with base64-encoded completed file
- Handles all document processing logic

**MCP Tool Definition:**
```python
@mcp.tool()
def complete_risk_document_base64(
    file_base64: str,
    filename: str = "document.xlsx"
) -> str:
    """Process Excel document from base64 and return completed document as base64."""
    # Returns JSON:
    # {
    #   "success": true,
    #   "message": "Document processing complete!",
    #   "file_base64": "UEsDBBQABgAI...",
    #   "filename": "document_completed.xlsx",
    #   "file_size_bytes": 52345
    # }
```

### Tool 3: File Decoder (Python Tool)

**File:** [`orchestrate_tools/orchestrate_decode_file.py`](risk-document-completion/orchestrate_tools/orchestrate_decode_file.py:1)

**Purpose:** Convert base64 output back to downloadable file

**Key Points:**
- Receives base64 string from MCP tool output
- Returns bytes directly for Orchestrate download
- Simple, focused functionality

**Orchestrate Tool Definition:**
```python
@tool()
def decode_base64_to_file(file_base64: str) -> bytes:
    """Decode base64 string and return as downloadable Excel file."""
    file_bytes = base64.b64decode(file_base64)
    return file_bytes
```

## Watson Orchestrate Skill Configuration

### Skill Definition (YAML)

```yaml
name: "Complete Risk Questionnaire"
description: "Auto-fill governance and compliance questionnaires using AI"

inputs:
  - name: uploaded_file
    type: file
    description: "Excel questionnaire to complete (.xlsx)"
    required: true

steps:
  # Step 1: Extract file from chat and encode to base64
  - name: encode_file
    tool: encode_file_to_base64
    inputs:
      # Orchestrate automatically extracts file_bytes from uploaded_file
      file_bytes: "{{ inputs.uploaded_file.content }}"
      filename: "{{ inputs.uploaded_file.name }}"
    outputs:
      - file_base64

  # Step 2: Process with MCP tool
  - name: process_document
    tool: complete_risk_document_base64
    inputs:
      file_base64: "{{ steps.encode_file.outputs.file_base64 }}"
      filename: "{{ inputs.uploaded_file.name }}"
    outputs:
      - success
      - message
      - file_base64
      - filename

  # Step 3: Decode to downloadable file
  - name: decode_file
    tool: decode_base64_to_file
    inputs:
      # Extract file_base64 from JSON response
      file_base64: "{{ steps.process_document.outputs.file_base64 }}"
    outputs:
      - file_bytes

outputs:
  - name: completed_file
    value: "{{ steps.decode_file.outputs.file_bytes }}"
    type: file
    filename: "{{ steps.process_document.outputs.filename }}"
  - name: status_message
    value: "{{ steps.process_document.outputs.message }}"
    type: string
```

### Alternative: Simplified Skill (Direct MCP Call)

If Orchestrate can extract JSON fields from MCP tool response:

```yaml
name: "Complete Risk Questionnaire - Simplified"
description: "Auto-fill questionnaires with fewer steps"

inputs:
  - name: uploaded_file
    type: file
    required: true

steps:
  # Step 1: Encode
  - name: encode
    tool: encode_file_to_base64
    inputs:
      file_bytes: "{{ inputs.uploaded_file.content }}"
      filename: "{{ inputs.uploaded_file.name }}"

  # Step 2: Process (MCP returns JSON with base64)
  - name: process
    tool: complete_risk_document_base64
    inputs:
      file_base64: "{{ steps.encode.outputs }}"
      filename: "{{ inputs.uploaded_file.name }}"

  # Step 3: Decode
  - name: decode
    tool: decode_base64_to_file
    inputs:
      file_base64: "{{ json_parse(steps.process.outputs).file_base64 }}"

outputs:
  - name: result
    value: "{{ steps.decode.outputs }}"
    type: file
```

## Deployment Steps

### 1. Deploy MCP Server

```bash
# Ensure MCP server is running and accessible
cd risk-document-completion/mcp_core
python mcp_server.py

# Or deploy to cloud/container
docker build -t risk-document-mcp .
docker run -p 8000:8000 risk-document-mcp
```

### 2. Register Python Tools in Orchestrate

```bash
# Activate Orchestrate environment
orchestrate env activate production

# Register encoder tool
cd orchestrate_tools
orchestrate tools import \
  --kind python \
  --file orchestrate_encode_file.py \
  --requirements-file orchestrate_tools_requirements.txt \
  --name "encode_file_to_base64" \
  --description "Convert uploaded Excel file to base64 for MCP processing"

# Register decoder tool
orchestrate tools import \
  --kind python \
  --file orchestrate_decode_file.py \
  --requirements-file orchestrate_tools_requirements.txt \
  --name "decode_base64_to_file" \
  --description "Convert base64 string to downloadable Excel file"
```

### 3. Register MCP Server in Orchestrate

```bash
# Register MCP server endpoint
orchestrate tools import mcp \
  --server-url "http://your-mcp-server:8000" \
  --name "complete_risk_document_base64" \
  --description "Auto-complete risk questionnaires using RAG"
```

### 4. Create Orchestrate Skill

Use the Orchestrate UI or CLI to create the skill with the YAML definition above.

## Testing

### Test Individual Tools

```bash
# Test encoder (with sample file)
python -c "
from orchestrate_encode_file import encode_file_to_base64
with open('tests/sample.xlsx', 'rb') as f:
    result = encode_file_to_base64(f.read(), 'sample.xlsx')
    print(f'Base64 length: {len(result)}')
"

# Test MCP tool (requires running server)
curl -X POST http://localhost:8000/tools/complete_risk_document_base64 \
  -H "Content-Type: application/json" \
  -d '{"file_base64": "UEsDBBQ...", "filename": "test.xlsx"}'

# Test decoder
python -c "
from orchestrate_decode_file import decode_base64_to_file
result = decode_base64_to_file('UEsDBBQ...')
print(f'File size: {len(result)} bytes')
"
```

### Test End-to-End in Orchestrate

1. Upload a sample Excel questionnaire in Orchestrate chat
2. Invoke the "Complete Risk Questionnaire" skill
3. Verify the completed file is returned for download

## Troubleshooting

### Issue: "File not found in chat history"

**Solution:** Ensure the file upload is properly referenced in the skill input:
```yaml
file_bytes: "{{ inputs.uploaded_file.content }}"
```

### Issue: "Invalid base64 encoding"

**Causes:**
- File was truncated during encoding
- Wrong parameter passed to MCP tool
- Network timeout during large file transfer

**Solution:**
- Check file size limits (Orchestrate may have limits)
- Verify base64 string is complete
- Add logging to encoder tool to verify output

### Issue: "MCP tool returns error"

**Debug steps:**
1. Check MCP server logs: `docker logs <container-id>`
2. Verify environment variables are set (`.env` file)
3. Test MCP tool directly with curl
4. Check AstraDB connectivity from MCP server

### Issue: "Downloaded file is corrupted"

**Causes:**
- Base64 decoding error
- File truncation during transfer
- Wrong content type in download

**Solution:**
- Verify base64 string integrity at each step
- Check Orchestrate file download configuration
- Ensure decoder returns raw bytes, not string

## Key Insights

### Why This Architecture?

1. **MCP Protocol Limitation:** MCP tools only accept JSON-serializable parameters (strings, numbers, objects), not binary data
2. **Orchestrate File Handling:** Files uploaded in chat are stored as references, not directly accessible to MCP tools
3. **Base64 Bridge:** Base64 encoding converts binary files to strings that can pass through MCP protocol

### Performance Considerations

- **File Size Limits:** Base64 encoding increases size by ~33%
- **Memory Usage:** Large files (>10MB) may cause memory issues
- **Processing Time:** Document processing depends on number of questions
- **Network Latency:** Three-tool chain adds overhead

### Security Considerations

- **Temporary Files:** MCP server creates temp files - ensure cleanup
- **API Keys:** Protect `.env` file with credentials
- **File Validation:** Tools validate `.xlsx` extension but consider adding virus scanning
- **HTTPS:** Use HTTPS for MCP server in production

## Alternative Solutions

### Option A: Direct File Upload to MCP (Future)

If MCP protocol adds binary support:
```python
@mcp.tool()
def complete_risk_document(file: bytes, filename: str) -> bytes:
    # Direct binary handling
    pass
```

### Option B: Orchestrate File Storage Integration

If Orchestrate provides file storage API:
```python
@tool()
def process_from_storage(file_id: str) -> str:
    # Fetch file from Orchestrate storage
    # Process and return result
    pass
```

### Option C: Streaming for Large Files

For files >50MB, consider streaming:
```python
@mcp.tool()
def complete_risk_document_chunked(
    file_chunk: str,
    chunk_index: int,
    total_chunks: int
) -> str:
    # Process file in chunks
    pass
```

## References

- [MCP Server Code](risk-document-completion/mcp_core/mcp_server.py)
- [Orchestrate Workflow Documentation](risk-document-completion/docs/ORCHESTRATE_WORKFLOW.md)
- [Encoder Tool](risk-document-completion/orchestrate_tools/orchestrate_encode_file.py)
- [Decoder Tool](risk-document-completion/orchestrate_tools/orchestrate_decode_file.py)
- [Watson Orchestrate Documentation](https://www.ibm.com/docs/en/watson-orchestrate)
- [MCP Protocol Specification](https://modelcontextprotocol.io)

## Next Steps

1. ✅ Review this solution document
2. ⬜ Test encoder tool with sample files
3. ⬜ Verify MCP server is accessible from Orchestrate
4. ⬜ Register all three tools in Orchestrate
5. ⬜ Create and test the skill definition
6. ⬜ Conduct end-to-end testing with real questionnaires
7. ⬜ Document any issues or improvements needed