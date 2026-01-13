# WatsonX Orchestrate Integration Guide

This guide explains how to integrate the Risk Document Completion MCP tool with IBM WatsonX Orchestrate, enabling users to upload Excel documents and receive completed versions with AI-generated answers.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Setup Instructions](#setup-instructions)
4. [Creating a Tool in WatsonX Orchestrate](#creating-a-tool-in-watsonx-orchestrate)
5. [Building a User Flow](#building-a-user-flow)
6. [Usage Examples](#usage-examples)
7. [Troubleshooting](#troubleshooting)

## Overview

The Risk Document Completion tool integrates with WatsonX Orchestrate to provide:

- **File Upload Interface**: Users upload Excel documents through Orchestrate's web interface
- **Automated Processing**: Documents are processed using LLM-based column detection and RAG
- **File Download**: Completed documents are returned for immediate download
- **No Manual Path Management**: All file handling is automated through bytes conversion

## Prerequisites

### 1. Environment Setup

Ensure you have the following configured:

```bash
# Required environment variables
MODEL_URL=<watsonx_url>
API_KEY=<api_key>
PROJECT_ID=<project_id>
SPACE_ID=<space_id>
MODEL=<model_id>
ASTRA_DB_API_ENDPOINT=<endpoint>
ASTRA_DB_APPLICATION_TOKEN=<token>
```

### 2. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 3. WatsonX Orchestrate Access

- Active WatsonX Orchestrate account
- Permissions to create custom tools and agents
- WatsonX Orchestrate ADK installed (optional, for advanced features)

## Setup Instructions

### Method 1: Deploying to IBM Code Engine (Recommended for Production)

IBM Code Engine provides a fully managed, serverless platform for hosting the MCP server. This is the recommended approach for production deployments with WatsonX Orchestrate.

#### Step 1: Prepare the Application

Create a `Dockerfile` in the project root:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY auto_complete_document.py .
COPY mcp_server.py .

# Expose port for HTTP endpoint (if needed)
EXPOSE 8080

# Set environment variables will be provided by Code Engine
ENV PYTHONUNBUFFERED=1

# Run the MCP server
CMD ["python", "mcp_server.py"]
```

#### Step 2: Create requirements.txt

Ensure your `requirements.txt` includes all dependencies:

```txt
pandas
openpyxl
ibm-watsonx-ai
python-dotenv
astrapy
sentence-transformers
mcp
fastmcp
```

#### Step 3: Deploy to IBM Code Engine

**Option A: Using IBM Cloud CLI**

```bash
# Install IBM Cloud CLI and Code Engine plugin
curl -fsSL https://clis.cloud.ibm.com/install/linux | sh
ibmcloud plugin install code-engine

# Login to IBM Cloud
ibmcloud login --sso

# Target your resource group and region
ibmcloud target -g <resource-group> -r <region>

# Create Code Engine project (first time only)
ibmcloud ce project create --name risk-document-completion

# Select the project
ibmcloud ce project select --name risk-document-completion

# Build and deploy from source
ibmcloud ce application create \
  --name risk-doc-completion \
  --build-source . \
  --strategy dockerfile \
  --port 8080 \
  --min-scale 0 \
  --max-scale 5 \
  --cpu 1 \
  --memory 2G \
  --env MODEL_URL=<your_watsonx_url> \
  --env API_KEY=<your_api_key> \
  --env PROJECT_ID=<your_project_id> \
  --env SPACE_ID=<your_space_id> \
  --env MODEL=<your_model_id> \
  --env ASTRA_DB_API_ENDPOINT=<your_astra_endpoint> \
  --env ASTRA_DB_APPLICATION_TOKEN=<your_astra_token>

# Get the application URL
ibmcloud ce application get --name risk-doc-completion
```

**Option B: Using Code Engine Web Console**

1. Navigate to [IBM Cloud Code Engine](https://cloud.ibm.com/codeengine/overview)
2. Create a new project: "risk-document-completion"
3. Click "Create Application"
4. Configure:
   - **Name**: `risk-doc-completion`
   - **Source**: Choose "Source code" or "Container image"
   - **Repository**: Link your Git repository or upload code
   - **Build strategy**: Dockerfile
   - **Port**: 8080 (if exposing HTTP endpoint)
   - **Resources**:
     - CPU: 1 vCPU
     - Memory: 2 GB
     - Min instances: 0 (serverless)
     - Max instances: 5
5. Add environment variables:
   - `MODEL_URL`
   - `API_KEY`
   - `PROJECT_ID`
   - `SPACE_ID`
   - `MODEL`
   - `ASTRA_DB_API_ENDPOINT`
   - `ASTRA_DB_APPLICATION_TOKEN`
6. Click "Create"

#### Step 4: Configure for WatsonX Orchestrate

Once deployed to Code Engine, configure your MCP server URL in WatsonX Orchestrate:

```bash
# Get your Code Engine application URL
ibmcloud ce application get --name risk-doc-completion --output url

# Register with Orchestrate
orchestrate tools add risk-document-completion \
  --url <your-code-engine-url> \
  --description "AI-powered risk document completion"
```

**Alternative: Use Code Engine as Backend for Local MCP Server**

If you want to keep the MCP protocol local but use Code Engine for processing:

1. Deploy the processing logic to Code Engine as a REST API
2. Have the local MCP server call the Code Engine endpoint
3. This provides scalability while maintaining MCP protocol compatibility

#### Benefits of IBM Code Engine Deployment

- **Serverless**: Scales to zero when not in use (no idle costs)
- **Auto-scaling**: Handles load spikes automatically
- **Managed Infrastructure**: No server maintenance required
- **Built-in Monitoring**: Logs and metrics in IBM Cloud console
- **CI/CD Integration**: Easy integration with GitHub Actions or IBM Toolchain
- **Environment Management**: Secure environment variable storage
- **High Availability**: Built-in redundancy and failover

#### Monitoring and Logs

```bash
# View application logs
ibmcloud ce application logs --name risk-doc-completion --follow

# Get application status
ibmcloud ce application get --name risk-doc-completion

# View application events
ibmcloud ce application events --name risk-doc-completion
```

---

### Method 2: Using WatsonX Orchestrate ADK (Local Development)

The WatsonX Orchestrate ADK provides the easiest way to register and manage tools.

#### Step 1: Install the ADK

```bash
pip install ibm-watsonx-orchestrate
```

#### Step 2: Create a Tool Definition

Create a file `orchestrate_tool.py`:

```python
from ibm_watsonx_orchestrate.agent_builder.tools import tool
from mcp_server import complete_risk_document_from_bytes

@tool
def complete_risk_document(file_bytes: bytes, filename: str = "document.xlsx") -> bytes:
    """
    Automatically complete risk assessment documents with AI-generated answers.

    Upload your Excel document with Q&A sections and receive a completed version.

    Args:
        file_bytes: The Excel file to process
        filename: Name of the uploaded file

    Returns:
        Completed Excel file ready for download
    """
    return complete_risk_document_from_bytes(
        file_bytes=file_bytes,
        filename=filename,
        return_as_bytes=True
    )
```

#### Step 3: Deploy to Orchestrate

```bash
# Login to your Orchestrate environment
orchestrate login --url <your-orchestrate-url>

# Register the tool
orchestrate tools add risk-document-completion \
  --file orchestrate_tool.py \
  --description "AI-powered risk document completion"

# Start the server
orchestrate server start
```

### Method 3: Manual Integration via MCP Protocol (Advanced)

If you prefer to use the MCP protocol directly:

#### Step 1: Start the MCP Server

```bash
python mcp_server.py
```

#### Step 2: Configure in Orchestrate

In your Orchestrate environment, add the MCP server configuration:

```json
{
  "tool_name": "risk-document-completion",
  "protocol": "mcp",
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
```

## Creating a Tool in WatsonX Orchestrate

### Option 1: Using Orchestrate Web UI

1. **Navigate to Tools**
   - Log into WatsonX Orchestrate
   - Go to "Tools" section
   - Click "Create New Tool"

2. **Configure Tool Settings**
   - Name: "Risk Document Completion"
   - Description: "AI-powered completion of governance and compliance documents"
   - Tool Type: Select "Custom Tool" or "MCP Tool"

3. **Define Input Parameters**
   - Parameter Name: `file_bytes`
   - Parameter Type: `File` or `bytes`
   - Display Name: "Document to Complete"
   - Description: "Upload your Excel document (.xlsx) with Q&A sections"
   - Required: Yes

   - Parameter Name: `filename`
   - Parameter Type: `String`
   - Display Name: "Filename"
   - Description: "Name of your document"
   - Required: No
   - Default: "document.xlsx"

4. **Define Output Parameters**
   - Parameter Name: `result`
   - Parameter Type: `File` or `bytes`
   - Display Name: "Completed Document"
   - Description: "Download your completed document"

5. **Link to MCP Server**
   - Point to the `complete_risk_document_from_bytes` tool
   - Verify connection and test

### Option 2: Using Flow Builder

Create a flow that handles the complete process:

```python
from ibm_watsonx_orchestrate.flow_builder.flows import Flow, flow, UserNode, START, END
from ibm_watsonx_orchestrate.flow_builder.types import UserFieldKind
from ibm_watsonx_orchestrate.flow_builder.data_map import DataMap, Assignment

@flow(
    name="complete_risk_document_flow",
    display_name="Complete Risk Document",
    description="Upload and complete governance documents"
)
def build_completion_flow(aflow: Flow = None) -> Flow:
    user_flow = aflow.userflow()

    # File upload node
    upload_node = user_flow.field(
        direction="input",
        name="upload_document",
        display_name="Upload Document",
        kind=UserFieldKind.File
    )

    # Tool execution node (implicit - Orchestrate handles this)
    # The tool is called with the uploaded file bytes

    # File download node
    data_map = DataMap()
    data_map.add(Assignment(
        target_variable="self.input.value",
        value_expression='flow["userflow_1"]["Upload Document"].output.value'
    ))

    download_node = user_flow.field(
        direction="output",
        name="download_completed",
        display_name="Download Completed Document",
        kind=UserFieldKind.File,
        input_map=data_map
    )

    # Connect nodes
    user_flow.edge(START, upload_node)
    user_flow.edge(upload_node, download_node)
    user_flow.edge(download_node, END)

    return aflow
```

## Usage Examples

### Example 1: Basic Document Completion

**User Workflow:**
1. Navigate to "Risk Document Completion" tool in Orchestrate
2. Click "Upload Document"
3. Select Excel file (e.g., `rfp_template.xlsx`)
4. Click "Process"
5. Wait for processing (typically 30-60 seconds)
6. Click "Download Completed Document"

**Behind the Scenes:**
```python
# User uploads file → Orchestrate converts to bytes
file_bytes = <uploaded_file_content>

# Orchestrate calls the tool
completed_bytes = complete_risk_document_from_bytes(
    file_bytes=file_bytes,
    filename="rfp_template.xlsx",
    return_as_bytes=True
)

# Orchestrate presents download link to user
# User downloads: rfp_template_completed.xlsx
```

### Example 2: Batch Processing with Agent

Create an agent that processes multiple documents:

```python
from ibm_watsonx_orchestrate.agent_builder import Agent

agent = Agent(
    name="document_completion_agent",
    description="Processes multiple risk documents"
)

@agent.task
def process_documents(document_list: list[bytes]) -> list[bytes]:
    """Process multiple documents in sequence"""
    completed_docs = []

    for i, doc_bytes in enumerate(document_list):
        completed = complete_risk_document_from_bytes(
            file_bytes=doc_bytes,
            filename=f"document_{i}.xlsx",
            return_as_bytes=True
        )
        completed_docs.append(completed)

    return completed_docs
```

### Example 3: Integration with Existing Workflow

Incorporate document completion into a larger governance workflow:

```python
@flow(name="governance_workflow")
def governance_flow(aflow: Flow = None) -> Flow:
    # Step 1: User uploads initial assessment
    upload = aflow.user_input(kind=UserFieldKind.File)

    # Step 2: Complete document with AI
    completed = aflow.tool_call(
        "complete_risk_document_from_bytes",
        inputs={"file_bytes": upload.output}
    )

    # Step 3: Review and approval
    review = aflow.user_review(
        document=completed.output,
        prompt="Review the AI-generated answers"
    )

    # Step 4: Submit for approval
    if review.approved:
        submit = aflow.tool_call(
            "submit_to_governance_system",
            inputs={"document": completed.output}
        )

    return aflow
```

## Troubleshooting

### Issue: "File not found" Error

**Cause:** Tool is trying to use file path instead of bytes

**Solution:** Ensure you're using `complete_risk_document_from_bytes`, not `complete_risk_document`

```python
# ❌ Wrong - uses file paths
complete_risk_document(input_file_path="/path/to/file.xlsx")

# ✅ Correct - uses bytes
complete_risk_document_from_bytes(file_bytes=uploaded_bytes)
```

### Issue: "Invalid file format" Error

**Cause:** File is not .xlsx format

**Solution:** Ensure uploaded files are Excel 2007+ format (.xlsx), not older .xls format

### Issue: Slow Processing

**Cause:** Large documents or many unanswered questions

**Solutions:**
1. Check document size (ideal: < 100 questions)
2. Verify RAG database is responding quickly
3. Consider processing sheets individually using `detect_qa_columns`

### Issue: Temporary Files Not Cleaned Up

**Cause:** Error during processing prevented cleanup

**Solution:** The tool automatically cleans up temp files, but you can manually remove them:

```bash
# List temp files
ls /tmp/*.xlsx

# Remove old temp files (older than 1 day)
find /tmp -name "*.xlsx" -mtime +1 -delete
```

### Issue: Model Initialization Timeout

**Cause:** First request takes longer to initialize the model

**Solution:**
- Expected behavior on first call (2-3 seconds)
- Subsequent calls use cached model (near-instant)
- Consider warming up the server before user access:

```python
# Warm-up script
from mcp_server import get_model
get_model()  # Initialize model cache
```

### Issue: RAG Returns No Context

**Cause:** Question doesn't match anything in knowledge base

**Solution:**
- Verify AstraDB collection contains relevant Q&A pairs
- Lower similarity threshold in `get_relevant_context`
- Add more training examples to the knowledge base

### Issue: Orchestrate Can't Find Tool

**Cause:** Tool registration or server connection issue

**Solution:**
```bash
# Check tool registration
orchestrate tools list

# Re-register if needed
orchestrate tools update risk-document-completion --file orchestrate_tool.py

# Restart server
orchestrate server restart
```

## Performance Optimization

### 1. Model Caching

The MCP server caches the LLM model on first use:
- First request: ~2-3 seconds (model initialization)
- Subsequent requests: Near-instant (cached model)

### 2. Concurrent Processing

For processing multiple documents, consider parallel execution:

```python
from concurrent.futures import ThreadPoolExecutor

def process_batch(documents: list[bytes]) -> list[bytes]:
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(
            lambda doc: complete_risk_document_from_bytes(doc),
            documents
        )
    return list(results)
```

### 3. RAG Query Optimization

Adjust RAG parameters for optimal performance:

```python
# In auto_complete_document.py:106
get_relevant_context(
    question=question,
    top_k=3,  # Reduce from 5 to 3 for faster queries
    similarity_threshold=0.6  # Increase from 0.5 for higher quality
)
```

## Security Best Practices

1. **Environment Variables**: Never commit credentials to version control
2. **File Validation**: Tool validates .xlsx format before processing
3. **Temporary Files**: Automatically cleaned up after processing
4. **Access Control**: Use Orchestrate's built-in access controls
5. **Audit Logging**: Enable logging for compliance tracking

```python
# Enhanced logging for audit trail
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('document_completion_audit.log'),
        logging.StreamHandler()
    ]
)
```

## Next Steps

1. **Test the Integration**: Use the test workflow in Orchestrate
2. **Train Users**: Provide documentation on file upload process
3. **Monitor Performance**: Track processing times and success rates
4. **Expand Knowledge Base**: Add more Q&A examples to AstraDB
5. **Customize Prompts**: Adjust system prompts in `auto_complete_document.py` for your use case

## Support

For issues or questions:
- Check the [MCP Server README](MCP_SERVER_README.md)
- Review the [CLAUDE.md](CLAUDE.md) for architecture details
- Consult [WatsonX Orchestrate documentation](https://developer.watson-orchestrate.ibm.com/)
- Contact your WatsonX Orchestrate administrator

## Additional Resources

- [WatsonX Orchestrate Developer Hub](https://developer.watson-orchestrate.ibm.com/)
- [WatsonX Orchestrate ADK Documentation](https://developer.watson-orchestrate.ibm.com/tools/create_tool)
- [Model Context Protocol Specification](https://github.com/anthropics/mcp)
- [FastMCP Documentation](https://github.com/anthropics/mcp)
