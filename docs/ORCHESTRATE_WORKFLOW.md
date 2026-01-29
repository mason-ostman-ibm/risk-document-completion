# WatsonX Orchestrate Integration Workflow

This document describes the complete workflow for integrating the Risk Document Completion tool with WatsonX Orchestrate using a three-tool chain.

## Overview

Since Orchestrate cannot directly pass file uploads to MCP tools, we use a three-tool workflow:

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATE WORKFLOW                         │
└─────────────────────────────────────────────────────────────────┘

1. User uploads Excel file
         ↓
2. Python Tool: orchestrate_encode_file.py
   - Input: File path from Orchestrate upload
   - Output: JSON with base64 string
         ↓
3. MCP Tool: complete_risk_document_base64
   - Input: base64 string + filename
   - Output: JSON with completed file as base64
         ↓
4. Python Tool: orchestrate_decode_file.py
   - Input: base64 string from MCP output
   - Output: File saved to download location
         ↓
5. User downloads completed file
```

## Tool Descriptions

### Tool 1: File Encoder (Python Tool)

**File:** `orchestrate_encode_file.py`
**Type:** Python Script (runs in Orchestrate)
**Purpose:** Convert uploaded Excel file to base64 string

**Input:**
```json
{
  "file_path": "/path/to/uploaded/file.xlsx"
}
```

**Output:**
```json
{
  "success": true,
  "file_base64": "UEsDBBQABgAIAAAAIQ...",
  "filename": "document.xlsx",
  "file_size_bytes": 45678,
  "error": null
}
```

**Registration in Orchestrate:**
```bash
# Register as Python tool in Orchestrate
orchestrate tools import python \
  --name "encode_excel_to_base64" \
  --script orchestrate_encode_file.py \
  --description "Convert Excel file to base64 for MCP processing"
```

---

### Tool 2: Document Processor (MCP Tool)

**Function:** `complete_risk_document_base64`
**Type:** MCP Tool (runs in MCP server)
**Purpose:** Process Excel document and auto-fill with RAG

**Input:**
```json
{
  "file_base64": "UEsDBBQABgAIAAAAIQ...",
  "filename": "risk_assessment.xlsx"
}
```

**Output:**
```json
{
  "success": true,
  "message": "Document processing complete!",
  "file_base64": "UEsDBBQABgAIAAAAIQ...",
  "filename": "risk_assessment_completed.xlsx",
  "file_size_bytes": 52345
}
```

**Registration in Orchestrate:**
```bash
# MCP server must be running and accessible to Orchestrate
# Register the MCP server endpoint in Orchestrate
orchestrate tools import mcp \
  --name "complete_risk_document_base64" \
  --server-url "http://your-mcp-server:8000" \
  --description "Auto-complete risk questionnaires using RAG"
```

---

### Tool 3: File Decoder (Python Tool)

**File:** `orchestrate_decode_file.py`
**Type:** Python Script (runs in Orchestrate)
**Purpose:** Convert base64 string back to downloadable Excel file

**Input:**
```json
{
  "file_base64": "UEsDBBQABgAIAAAAIQ...",
  "output_path": "/path/to/downloads/completed_document.xlsx"
}
```

**Output:**
```json
{
  "success": true,
  "file_path": "/path/to/downloads/completed_document.xlsx",
  "filename": "completed_document.xlsx",
  "file_size_bytes": 52345,
  "error": null
}
```

**Registration in Orchestrate:**
```bash
# Register as Python tool in Orchestrate
orchestrate tools import python \
  --name "decode_base64_to_excel" \
  --script orchestrate_decode_file.py \
  --description "Convert base64 string to downloadable Excel file"
```

---

## Complete Orchestrate Skill Definition

Create an Orchestrate skill that chains these three tools together:

```yaml
name: "Complete Risk Questionnaire"
description: "Auto-fill governance and compliance questionnaires using AI"

inputs:
  - name: uploaded_file
    type: file
    description: "Excel questionnaire to complete (.xlsx)"
    required: true

steps:
  # Step 1: Encode the uploaded file
  - name: encode_file
    tool: encode_excel_to_base64
    inputs:
      file_path: "{{ inputs.uploaded_file.path }}"
    outputs:
      - file_base64
      - filename

  # Step 2: Process with MCP tool
  - name: process_document
    tool: complete_risk_document_base64
    inputs:
      file_base64: "{{ steps.encode_file.outputs.file_base64 }}"
      filename: "{{ steps.encode_file.outputs.filename }}"
    outputs:
      - file_base64
      - filename
      - message

  # Step 3: Decode to downloadable file
  - name: decode_file
    tool: decode_base64_to_excel
    inputs:
      file_base64: "{{ steps.process_document.outputs.file_base64 }}"
      output_path: "/tmp/{{ steps.process_document.outputs.filename }}"
    outputs:
      - file_path
      - file_size_bytes

outputs:
  - name: completed_file
    value: "{{ steps.decode_file.outputs.file_path }}"
    type: file
  - name: status_message
    value: "{{ steps.process_document.outputs.message }}"
    type: string
```

---

## Testing the Workflow

### Test Tool 1: Encoder

```bash
# Test encoding a sample file
python orchestrate_encode_file.py testing/sample_rfp.xlsx

# Expected output:
# {"success": true, "file_base64": "UEsDBBQ...", "filename": "sample_rfp.xlsx", ...}
```

### Test Tool 2: MCP Tool (via MCP server)

```bash
# Start MCP server
python mcp_server.py

# In another terminal, test with base64 input
# (You'll need to pass the actual base64 string from Tool 1 output)
```

### Test Tool 3: Decoder

```bash
# Test decoding (use base64 string from Tool 2 output)
python orchestrate_decode_file.py "UEsDBBQABgAI..." /tmp/output.xlsx

# Expected output:
# {"success": true, "file_path": "/tmp/output.xlsx", ...}
```

### Integration Test

Run the complete workflow:

```bash
# 1. Encode
ENCODE_OUTPUT=$(python orchestrate_encode_file.py testing/sample_rfp.xlsx)
FILE_BASE64=$(echo $ENCODE_OUTPUT | jq -r '.file_base64')

# 2. Process (assuming MCP server running on localhost:8000)
# This step requires calling the MCP server - example using curl:
MCP_OUTPUT=$(curl -X POST http://localhost:8000/tools/complete_risk_document_base64 \
  -H "Content-Type: application/json" \
  -d "{\"file_base64\": \"$FILE_BASE64\", \"filename\": \"sample_rfp.xlsx\"}")

RESULT_BASE64=$(echo $MCP_OUTPUT | jq -r '.file_base64')

# 3. Decode
python orchestrate_decode_file.py "$RESULT_BASE64" /tmp/completed.xlsx

# Check the output file
ls -lh /tmp/completed.xlsx
```

---

## Deployment Checklist

- [ ] Deploy MCP server to accessible endpoint (Cloud, VM, etc.)
- [ ] Register `orchestrate_encode_file.py` as Python tool in Orchestrate
- [ ] Register `orchestrate_decode_file.py` as Python tool in Orchestrate
- [ ] Register MCP server endpoint in Orchestrate
- [ ] Create Orchestrate skill that chains the three tools
- [ ] Test end-to-end workflow with sample Excel file
- [ ] Configure file upload/download paths in Orchestrate environment
- [ ] Set up environment variables (.env) for MCP server
- [ ] Verify AstraDB connectivity from MCP server
- [ ] Test error handling (invalid files, network issues, etc.)

---

## Error Handling

Each tool returns structured JSON with a `success` field. In your Orchestrate skill, check for errors at each step:

```yaml
steps:
  - name: encode_file
    tool: encode_excel_to_base64
    inputs:
      file_path: "{{ inputs.uploaded_file.path }}"
    on_error:
      action: fail
      message: "Failed to encode file: {{ error.message }}"
```

---

## Troubleshooting

### Tool 1 Fails (Encoder)
- Check file path is absolute and file exists
- Verify file has .xlsx extension
- Check file permissions (readable by Orchestrate)

### Tool 2 Fails (MCP Tool)
- Verify MCP server is running and accessible
- Check base64 string is valid (not truncated)
- Review MCP server logs for errors
- Verify environment variables (.env) are set correctly
- Test AstraDB connection from MCP server

### Tool 3 Fails (Decoder)
- Verify output path is writable by Orchestrate
- Check base64 string from MCP output is valid
- Ensure output directory exists or tool can create it

### Performance Issues
- Large files (>10MB) may take longer to encode/decode
- MCP processing time depends on document size and number of questions
- Consider implementing timeout handlers in Orchestrate skill

---

## Security Considerations

- **File Validation:** Tools validate .xlsx extension, but consider adding virus scanning
- **Base64 Size Limits:** Very large files may exceed Orchestrate message size limits
- **Temporary Files:** Ensure temporary files are cleaned up after processing
- **API Keys:** MCP server .env file contains sensitive credentials - protect appropriately
- **Network Security:** Use HTTPS for MCP server endpoint in production

---

## Next Steps

1. Review the three Python files:
   - `orchestrate_encode_file.py`
   - `orchestrate_decode_file.py`
   - `mcp_server.py` (already exists)

2. Test each tool individually before chaining

3. Create the Orchestrate skill definition

4. Deploy and test end-to-end workflow

For questions or issues, refer to:
- `MCP_SERVER_README.md` - MCP server documentation
- `QUICKSTART.md` - Quick start guide
- `CLAUDE.md` - Development guidelines
