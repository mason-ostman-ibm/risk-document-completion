# Quick Fix Guide: Orchestrate File Handling

## The Problem

Your MCP tool expects a base64 string, but Orchestrate chat history has the file as bytes. You need a bridge between them.

## The Solution (3 Tools)

```
User Upload → Python Tool (encode) → MCP Tool (process) → Python Tool (decode) → Download
```

## What Already Exists ✅

All three tools are already implemented:

1. **Encoder:** [`orchestrate_tools/orchestrate_encode_file.py`](orchestrate_tools/orchestrate_encode_file.py)
2. **MCP Processor:** [`mcp_core/mcp_server.py`](mcp_core/mcp_server.py) - `complete_risk_document_base64()`
3. **Decoder:** [`orchestrate_tools/orchestrate_decode_file.py`](orchestrate_tools/orchestrate_decode_file.py)

## What You Need to Do

### Step 1: Register Python Tools in Orchestrate

```bash
# Navigate to orchestrate_tools directory
cd orchestrate_tools

# Register encoder
orchestrate tools import \
  --kind python \
  --file orchestrate_encode_file.py \
  --requirements-file orchestrate_tools_requirements.txt

# Register decoder
orchestrate tools import \
  --kind python \
  --file orchestrate_decode_file.py \
  --requirements-file orchestrate_tools_requirements.txt
```

### Step 2: Register MCP Server

```bash
# Make sure your MCP server is running and accessible
# Then register it in Orchestrate
orchestrate tools import mcp \
  --server-url "http://your-mcp-server:8000" \
  --tool-name "complete_risk_document_base64"
```

### Step 3: Create Orchestrate Skill

Create a skill that chains the three tools:

```yaml
name: "Complete Risk Questionnaire"

inputs:
  - name: uploaded_file
    type: file
    required: true

steps:
  # Step 1: Encode file from chat to base64
  - name: encode
    tool: encode_file_to_base64
    inputs:
      file_bytes: "{{ inputs.uploaded_file.content }}"
      filename: "{{ inputs.uploaded_file.name }}"

  # Step 2: Process with MCP
  - name: process
    tool: complete_risk_document_base64
    inputs:
      file_base64: "{{ steps.encode.outputs }}"
      filename: "{{ inputs.uploaded_file.name }}"

  # Step 3: Decode back to file
  - name: decode
    tool: decode_base64_to_file
    inputs:
      file_base64: "{{ json_parse(steps.process.outputs).file_base64 }}"

outputs:
  - name: completed_file
    value: "{{ steps.decode.outputs }}"
    type: file
```

## How It Works

1. **User uploads Excel file** in Orchestrate chat
2. **Encoder tool** extracts file bytes from chat and converts to base64 string
3. **MCP tool** receives base64, processes document, returns base64 result
4. **Decoder tool** converts base64 back to bytes for download
5. **User downloads** completed file

## Key Points

- **Why base64?** MCP protocol only accepts JSON-serializable data (strings, not binary)
- **File extraction:** Orchestrate automatically provides `file_bytes` from uploaded files
- **JSON parsing:** MCP tool returns JSON, so you need to extract the `file_base64` field
- **All tools exist:** You just need to register and chain them

## Testing

Test each tool individually:

```bash
# Test encoder
python orchestrate_tools/orchestrate_encode_file.py

# Test MCP (with server running)
curl -X POST http://localhost:8000/tools/complete_risk_document_base64 \
  -H "Content-Type: application/json" \
  -d '{"file_base64": "...", "filename": "test.xlsx"}'

# Test decoder
python orchestrate_tools/orchestrate_decode_file.py
```

## Troubleshooting

**"File not found"**
- Check skill input: `file_bytes: "{{ inputs.uploaded_file.content }}"`

**"Invalid base64"**
- Verify encoder output is complete
- Check for truncation in large files

**"MCP tool error"**
- Check MCP server logs
- Verify server is accessible from Orchestrate
- Test with curl first

## Full Documentation

See [`ORCHESTRATE_FILE_HANDLING_SOLUTION.md`](ORCHESTRATE_FILE_HANDLING_SOLUTION.md) for complete details.

## Summary

✅ **All code exists** - no new development needed  
✅ **Just register tools** in Orchestrate  
✅ **Create skill** to chain them together  
✅ **Test end-to-end** with sample file  

The solution bridges the gap between Orchestrate's file handling and MCP's string-based protocol using base64 encoding.