# Risk Document Completion MCP Server

This MCP (Model Context Protocol) server exposes document completion functionality as tools that can be used by WatsonX Orchestrate and other MCP-compatible clients.

## Overview

The MCP server provides six main tools for automated document completion:

1. **complete_risk_document** - Process entire Excel documents with Q&A sections (file path based)
2. **complete_risk_document_from_bytes** - Process Excel documents from bytes (optimized for Orchestrate)
3. **detect_qa_columns** - Identify question and answer columns in a sheet
4. **answer_single_question** - Answer individual questions with RAG
5. **search_knowledge_base** - Search for relevant Q&A examples
6. **list_excel_sheets** - List all sheets in an Excel workbook

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# IBM WatsonX AI Configuration
MODEL_URL=<watsonx_url>
API_KEY=<api_key>
PROJECT_ID=<project_id>
SPACE_ID=<space_id>
MODEL=<model_id>

# AstraDB Vector Database Configuration
ASTRA_DB_API_ENDPOINT=<endpoint>
ASTRA_DB_APPLICATION_TOKEN=<token>
```

## Running the MCP Server

### Standalone Mode

Run the server directly:

```bash
python mcp_server.py
```

The server will start and listen for MCP protocol messages on stdin/stdout.

### With WatsonX Orchestrate

#### Option 1: Using WatsonX Orchestrate ADK

1. Install the WatsonX Orchestrate ADK:
```bash
pip install ibm-watsonx-orchestrate
```

2. Configure the MCP server in your Orchestrate environment:
```bash
orchestrate tools add risk-document-completion \
  --command "python /path/to/mcp_server.py" \
  --description "Automated risk document completion with RAG"
```

3. Start the Orchestrate server:
```bash
orchestrate server start -e .my-env
```

#### Option 2: Using Claude Desktop or Other MCP Clients

Add to your MCP client configuration (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "risk-document-completion": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_server.py"],
      "env": {
        "MODEL_URL": "<your_watsonx_url>",
        "API_KEY": "<your_api_key>",
        "PROJECT_ID": "<your_project_id>",
        "SPACE_ID": "<your_space_id>",
        "MODEL": "<your_model_id>",
        "ASTRA_DB_API_ENDPOINT": "<your_astra_endpoint>",
        "ASTRA_DB_APPLICATION_TOKEN": "<your_astra_token>"
      }
    }
  }
}
```

## Available Tools

### 1. complete_risk_document

Process an entire Excel document and fill in unanswered questions (file path based).

**NOTE:** For WatsonX Orchestrate integration with file uploads/downloads, use `complete_risk_document_from_bytes` instead.

**Parameters:**
- `input_file_path` (required): Absolute path to the input Excel file
- `output_file_path` (optional): Absolute path for the output file

**Example:**
```python
complete_risk_document(
    input_file_path="/path/to/rfp_document.xlsx",
    output_file_path="/path/to/rfp_document_completed.xlsx"
)
```

**Returns:**
Success message with the output file path.

---

### 2. complete_risk_document_from_bytes

Process an Excel document from bytes and return the completed document (optimized for WatsonX Orchestrate).

This tool is specifically designed for WatsonX Orchestrate integration where:
- Users upload files through the Orchestrate interface
- Files are provided as bytes to the tool
- The completed file is returned as bytes for immediate download

**Parameters:**
- `file_bytes` (required): Excel file content as bytes
- `filename` (optional): Original filename, default: "document.xlsx"
- `return_as_bytes` (optional): If True (default), returns bytes. If False, returns file path.

**Example:**
```python
# In WatsonX Orchestrate flow
completed_bytes = complete_risk_document_from_bytes(
    file_bytes=uploaded_file_bytes,
    filename="risk_assessment.xlsx",
    return_as_bytes=True
)
```

**Returns:**
- If `return_as_bytes=True`: Completed Excel file as bytes (ready for download)
- If `return_as_bytes=False`: Success message with temporary file path

**WatsonX Orchestrate Integration:**
When creating a tool in Orchestrate:
1. Set input parameter type to `File` or `bytes`
2. Set output parameter type to `File` or `bytes`
3. Users can upload their document and receive the completed version immediately

---

### 3. detect_qa_columns

Detect which columns contain questions and answers in a specific sheet.

**Parameters:**
- `file_path` (required): Absolute path to the Excel file
- `sheet_name` (required): Name of the sheet to analyze

**Example:**
```python
detect_qa_columns(
    file_path="/path/to/document.xlsx",
    sheet_name="Risk Assessment"
)
```

**Returns:**
JSON with detected column names:
```json
{"question_column": "Question", "answer_column": "Response"}
```

---

### 4. answer_single_question

Answer a single question using the LLM with optional RAG context.

**Parameters:**
- `question` (required): The question to answer
- `use_rag` (optional, default=True): Whether to use RAG for context
- `top_k` (optional, default=5): Number of similar examples to retrieve

**Example:**
```python
answer_single_question(
    question="What is IBM's data retention policy?",
    use_rag=True,
    top_k=5
)
```

**Returns:**
Generated answer to the question.

---

### 5. search_knowledge_base

Search the knowledge base for relevant Q&A examples.

**Parameters:**
- `query` (required): Search query or question
- `top_k` (optional, default=5): Maximum number of results
- `similarity_threshold` (optional, default=0.5): Minimum similarity score

**Example:**
```python
search_knowledge_base(
    query="security compliance requirements",
    top_k=5,
    similarity_threshold=0.5
)
```

**Returns:**
Formatted string with relevant Q&A examples.

---

### 6. list_excel_sheets

List all sheet names in an Excel workbook.

**Parameters:**
- `file_path` (required): Absolute path to the Excel file

**Example:**
```python
list_excel_sheets(file_path="/path/to/document.xlsx")
```

**Returns:**
JSON with sheet names and count:
```json
{"sheets": ["Sheet1", "Risk Assessment", "Compliance"], "total_count": 3}
```

## Architecture

### MCP Protocol Integration

The server uses the FastMCP framework from the MCP Python SDK. It:
- Implements the Model Context Protocol for tool exposure
- Communicates via stdin/stdout using JSON-RPC
- Supports both synchronous and asynchronous operations
- Provides structured input/output schemas for all tools

### Backend Integration

The MCP server acts as a wrapper around the existing `auto_complete_document.py` functionality:

```
MCP Client (WatsonX Orchestrate)
       ↓
MCP Server (mcp_server.py)
       ↓
Document Processing (auto_complete_document.py)
       ↓
┌──────┴──────┐
│             │
LLM (WatsonX) RAG (AstraDB)
```

### Model Caching

The LLM model is cached on first use to improve performance:
- First tool call initializes the model (~2-3 seconds)
- Subsequent calls reuse the cached model (instant)
- Cache persists for the lifetime of the server process

## Testing

### Test Individual Tools

You can test tools using any MCP client or the MCP inspector:

```bash
# Install MCP inspector
npm install -g @modelcontextprotocol/inspector

# Run inspector
mcp-inspector python mcp_server.py
```

### Test with Sample Document

```bash
# Create a test Excel file with Q&A columns
# Then run:
python -c "
from mcp_server import complete_risk_document
result = complete_risk_document('/path/to/test.xlsx')
print(result)
"
```

## Troubleshooting

### Server Won't Start

1. Verify all environment variables are set:
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('MODEL_URL'))"
```

2. Check Python version (3.8+ required):
```bash
python --version
```

3. Verify all dependencies are installed:
```bash
pip list | grep mcp
```

### Model Initialization Errors

- Verify WatsonX credentials are correct
- Check that the MODEL_URL is accessible
- Ensure the PROJECT_ID and MODEL are valid

### RAG/Database Errors

- Verify AstraDB endpoint and token are correct
- Check that the `qa_collection` exists in your database
- Test database connectivity:
```python
from astrapy import DataAPIClient
client = DataAPIClient(os.getenv("ASTRA_DB_APPLICATION_TOKEN"))
db = client.get_database(os.getenv("ASTRA_DB_API_ENDPOINT"))
print(db.list_collection_names())
```

## Performance Considerations

- **First Call Latency**: Initial tool calls take 2-3 seconds to initialize the model
- **Subsequent Calls**: Near-instant due to model caching
- **Large Documents**: Processing time scales linearly with number of unanswered questions
- **RAG Queries**: Vector searches typically complete in <100ms

## Security Notes

- The server runs with the permissions of the user who starts it
- File paths must be absolute to prevent directory traversal
- Environment variables should never be committed to version control
- Use `.env` files for local development only
- In production, use secure secret management (e.g., IBM Secrets Manager)

## License

Internal IBM tool - See project license.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the main project documentation in `CLAUDE.md`
3. Contact the development team
