# Quick Start Guide - Risk Document Completion MCP Server

This guide will help you get the MCP server running in under 5 minutes.

## Prerequisites

- Python 3.8 or higher
- pip package manager
- Access to IBM WatsonX AI
- Access to AstraDB (for RAG)

## Step 1: Install Dependencies

```bash
# Navigate to the project directory
cd /path/to/risk_document_completion_MCP_tool

# Install Python packages
pip install -r requirements.txt
```

## Step 2: Configure Environment

Create a `.env` file in the project root:

```bash
# Copy the example and edit with your credentials
cat > .env << EOF
MODEL_URL=https://us-south.ml.cloud.ibm.com
API_KEY=your_watsonx_api_key_here
PROJECT_ID=your_project_id_here
SPACE_ID=your_space_id_here
MODEL=meta-llama/llama-3-1-70b-instruct
ASTRA_DB_API_ENDPOINT=https://your-db-id.apps.astra.datastax.com
ASTRA_DB_APPLICATION_TOKEN=your_astra_token_here
EOF
```

## Step 3: Test the Server

Test that the server starts correctly:

```bash
python mcp_server.py
```

You should see:
```
INFO:__main__:Starting Risk Document Completion MCP Server...
```

Press `Ctrl+C` to stop the test.

## Step 4: Use with WatsonX Orchestrate

### Option A: Command Line Registration

```bash
# Install WatsonX Orchestrate ADK
pip install ibm-watsonx-orchestrate

# Register the MCP server
orchestrate tools add risk-document-completion \
  --command "python $(pwd)/mcp_server.py" \
  --description "Automated risk document completion"

# Start Orchestrate
orchestrate server start
```

### Option B: Configuration File

1. Copy the example config:
```bash
cp watsonx_orchestrate_config.yaml ~/.orchestrate/config.yaml
```

2. Edit the file and update the absolute path to `mcp_server.py`

3. Start Orchestrate:
```bash
orchestrate server start
```

## Step 5: Use with Claude Desktop (Alternative)

If you want to use the MCP server with Claude Desktop instead:

1. Find your Claude Desktop config file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. Add the MCP server configuration:
```json
{
  "mcpServers": {
    "risk-document-completion": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_server.py"],
      "env": {
        "MODEL_URL": "your_url",
        "API_KEY": "your_key",
        "PROJECT_ID": "your_project_id",
        "SPACE_ID": "your_space_id",
        "MODEL": "meta-llama/llama-3-1-70b-instruct",
        "ASTRA_DB_API_ENDPOINT": "your_endpoint",
        "ASTRA_DB_APPLICATION_TOKEN": "your_token"
      }
    }
  }
}
```

3. Restart Claude Desktop

## Testing Your Setup

### Test 1: List Sheets in a Document

Create a simple test Excel file or use an existing one:

```python
# In Python
from mcp_server import list_excel_sheets
result = list_excel_sheets("/path/to/your/document.xlsx")
print(result)
```

Expected output:
```json
{"sheets": ["Sheet1", "Sheet2"], "total_count": 2}
```

### Test 2: Answer a Question

```python
from mcp_server import answer_single_question
result = answer_single_question("What is IBM's mission?", use_rag=False)
print(result)
```

### Test 3: Complete a Document

```python
from mcp_server import complete_risk_document
result = complete_risk_document(
    input_file_path="/path/to/rfp.xlsx",
    output_file_path="/path/to/rfp_completed.xlsx"
)
print(result)
```

## Available Tools

Once the MCP server is running, you have access to these tools:

1. **complete_risk_document** - Process entire documents
2. **detect_qa_columns** - Find Q&A columns in sheets
3. **answer_single_question** - Answer individual questions
4. **search_knowledge_base** - Search the RAG database
5. **list_excel_sheets** - List sheets in a workbook

## Example Usage in WatsonX Orchestrate

Once registered, you can use natural language commands:

- "Complete the risk document at /path/to/rfp.xlsx"
- "What questions can you answer about security compliance?"
- "List all sheets in my governance document"
- "Detect the Q&A columns in the Risk Assessment sheet"

## Troubleshooting

### "Module not found" errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### "Connection refused" errors

Check your WatsonX credentials:
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API_KEY:', os.getenv('API_KEY')[:10] + '...')"
```

### "Collection not found" errors

Verify your AstraDB collection exists:
```bash
python -c "
from dotenv import load_dotenv
import os
from astrapy import DataAPIClient
load_dotenv()
client = DataAPIClient(os.getenv('ASTRA_DB_APPLICATION_TOKEN'))
db = client.get_database(os.getenv('ASTRA_DB_API_ENDPOINT'))
print('Collections:', db.list_collection_names())
"
```

The output should include `qa_collection`.

## Next Steps

- Read the full documentation in `MCP_SERVER_README.md`
- Review the implementation in `mcp_server.py`
- Check the original functionality in `auto_complete_document.py`
- See `CLAUDE.md` for architecture details

## Getting Help

For issues:
1. Check the Troubleshooting section above
2. Review error messages in the server logs
3. Verify all environment variables are set correctly
4. Test individual components (WatsonX, AstraDB) separately

## Performance Tips

- The first tool call takes 2-3 seconds (model initialization)
- Subsequent calls are near-instant (model is cached)
- Large documents process at ~2-3 seconds per question
- Keep the server running to maintain the model cache

Happy document completing! 🚀
