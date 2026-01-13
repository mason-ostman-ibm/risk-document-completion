# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Risk Document Completion MCP (Model Context Protocol) Tool that automatically processes Excel-based governance, compliance, and business documents. It uses LLM-based column detection combined with RAG (Retrieval-Augmented Generation) to intelligently fill out Q&A sections in spreadsheets.

## Architecture

### Two-Stage Processing Pipeline

1. **Column Detection Stage** (`detect_qa_columns_in_sheet`)
   - Uses LLM to analyze spreadsheet structure
   - Identifies which columns contain questions vs answers
   - Returns column names for downstream processing
   - Located in `auto_complete_document.py:60-104`

2. **Answer Generation Stage** (`ask_llm`)
   - Retrieves relevant context from AstraDB vector database
   - Generates answers using IBM WatsonX AI LLM
   - Fills answers into Excel workbook using openpyxl
   - Located in `auto_complete_document.py:153-218`

### RAG (Retrieval-Augmented Generation) System

The RAG implementation (`get_relevant_context` in `auto_complete_document.py:106-151`) works as follows:
- Questions are embedded using `ibm-granite/granite-embedding-30m-english` model
- Vector search performed against AstraDB `qa_collection`
- Top-k results filtered by similarity threshold (default 0.5)
- Context formatted and injected into LLM prompt
- Filters out unanswered examples to avoid propagating empty answers

### Excel Document Processing

Multi-sheet processing loop (`process_document` in `auto_complete_document.py:220-366`):
- Iterates through all sheets in workbook
- For each sheet: detects Q&A columns → finds unanswered questions → generates answers → formats cells
- Handles merged cells by unmerging before writing
- Applies professional formatting (wrap text, column widths, row heights)

### MCP Server Integration

The MCP server (`mcp_server.py`) wraps the document completion functionality as Model Context Protocol tools:
- **FastMCP Framework** - Uses MCP Python SDK for protocol implementation
- **Six Tools Exposed**:
  1. `complete_risk_document` - Process entire Excel documents (file path based)
  2. `complete_risk_document_from_bytes` - Process Excel documents from bytes (optimized for Orchestrate)
  3. `detect_qa_columns` - Identify Q&A columns in sheets
  4. `answer_single_question` - Answer individual questions with RAG
  5. `search_knowledge_base` - Search AstraDB for relevant examples
  6. `list_excel_sheets` - List all sheets in a workbook
- **Model Caching** - LLM model is cached on first use for performance
- **WatsonX Orchestrate Integration** - Fully integrated with Orchestrate for file upload/download workflows
  - Users can upload Excel files through Orchestrate UI
  - Files are processed as bytes (no manual path management)
  - Completed files are returned as bytes for immediate download
  - See `ORCHESTRATE_INTEGRATION.md` for detailed setup guide
- **Claude Desktop Integration** - Compatible with Claude Desktop MCP client

## Key Files

- **`auto_complete_document.py`** - Main document processing pipeline with full RAG integration
- **`detect_qa_columns.py`** - Standalone testing script for column detection (development utility)
- **`mcp_server.py`** - MCP (Model Context Protocol) server that exposes document completion as tools for WatsonX Orchestrate
- **`MCP_SERVER_README.md`** - Comprehensive documentation for the MCP server
- **`ORCHESTRATE_INTEGRATION.md`** - Complete guide for integrating with WatsonX Orchestrate (file upload/download workflows)
- **`QUICKSTART.md`** - Quick start guide for getting the MCP server running

## Environment Setup

### Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install pandas openpyxl ibm-watsonx-ai python-dotenv astrapy sentence-transformers
```

### Required Environment Variables (.env)

```
MODEL_URL=<watsonx_url>           # IBM WatsonX AI endpoint
API_KEY=<api_key>                 # WatsonX AI API key
PROJECT_ID=<project_id>           # WatsonX AI project ID
SPACE_ID=<space_id>              # WatsonX AI space ID (optional)
MODEL=<model_id>                  # Model identifier (e.g., meta-llama/llama-3-1-70b-instruct)
ASTRA_DB_API_ENDPOINT=<endpoint>  # AstraDB vector database endpoint
ASTRA_DB_APPLICATION_TOKEN=<token> # AstraDB access token
```

## Running the Tool

### Standalone Usage

```bash
# Process a document (creates *_completed.xlsx)
python auto_complete_document.py input_file.xlsx

# Specify custom output file
python auto_complete_document.py input_file.xlsx output_file.xlsx
```

### MCP Server Usage

```bash
# Run as MCP server (for WatsonX Orchestrate or Claude Desktop)
python mcp_server.py

# Quick test of MCP server
python -c "from mcp_server import list_excel_sheets; print(list_excel_sheets('/path/to/file.xlsx'))"
```

See `QUICKSTART.md` for detailed MCP setup instructions.

### Testing Column Detection

```bash
# Test column detection on a specific sheet
python detect_qa_columns.py
```

Note: Edit the file path and sheet number in the `__main__` block before running.

## Important Implementation Details

### LLM Configuration

- **Temperature: 0** - Deterministic outputs for form-filling consistency
- **Top-p: 1** - Full probability distribution (combined with temp=0 for consistency)
- System prompt trains model to write as if completing official IBM forms

### Cell Handling

When writing to Excel cells, the code must handle merged cells:
1. Check if cell is `MergedCell` instance
2. Find containing merge range
3. Unmerge the range
4. Re-acquire cell reference (merged cells become regular cells after unmerge)
5. Write value and apply formatting

See `auto_complete_document.py:313-336` for implementation.

### RAG Context Filtering

The `get_relevant_context` function filters retrieved examples:
- Removes answers marked as "unanswered", "nan", "none", "n/a", or empty strings
- Only includes results above similarity threshold
- Returns fallback message if no relevant context found

This prevents the model from learning to output "unanswered" from bad training examples.

## Development Notes

### Hardcoded Username

The username `mason.ostman@ibm.com` is hardcoded in both files for WatsonX credentials initialization. When modifying authentication, update both:
- `auto_complete_document.py:37`
- `detect_qa_columns.py:14`

### AstraDB Collection

The vector database collection name is hardcoded as `qa_collection` in `auto_complete_document.py:28`. This collection must exist and contain documents with fields:
- `question` (text)
- `answer` (text)
- `$vector` (embedding vector)
- `category` (metadata, optional)
- `source_file` (metadata, optional)
