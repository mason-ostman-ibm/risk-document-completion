#!/usr/bin/env python3
"""
Risk Document Completion MCP Server
Exposes document completion functionality as MCP tools for WatsonX Orchestrate
"""

import os
import logging
import tempfile
import base64
from typing import Optional, Union
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Import our existing document processing functions
from auto_complete_document import (
    initialize_model,
    detect_qa_columns_in_sheet,
    process_document,
    get_relevant_context,
    ask_llm
)

import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server instance
mcp = FastMCP("risk-document-completion")

# Cache the model to avoid re-initialization on every call
_model_cache = None


def get_model():
    """Get or initialize the LLM model (cached)"""
    global _model_cache
    if _model_cache is None:
        logger.info("Initializing LLM model...")
        _model_cache = initialize_model()
        logger.info("Model initialized successfully")
    return _model_cache


def bytes_to_temp_file(file_bytes: bytes, filename: str = "document.xlsx") -> str:
    """
    Convert bytes to a temporary file and return the file path.

    Args:
        file_bytes: File content as bytes
        filename: Original filename (used for extension)

    Returns:
        Path to the temporary file
    """
    suffix = Path(filename).suffix or '.xlsx'
    temp_file = tempfile.NamedTemporaryFile(mode='wb', suffix=suffix, delete=False)
    temp_file.write(file_bytes)
    temp_file.close()
    logger.info(f"Created temporary file: {temp_file.name}")
    return temp_file.name


def file_to_bytes(file_path: str) -> bytes:
    """
    Read a file and return its content as bytes.

    Args:
        file_path: Path to the file

    Returns:
        File content as bytes
    """
    with open(file_path, 'rb') as f:
        return f.read()


def cleanup_temp_file(file_path: str):
    """
    Delete a temporary file if it exists.

    Args:
        file_path: Path to the temporary file
    """
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.info(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to clean up temporary file {file_path}: {e}")


@mcp.tool()
def complete_risk_document(
    input_file_path: str,
    output_file_path: Optional[str] = None
) -> str:
    """
    Process an Excel document and automatically fill in unanswered questions using RAG.

    NOTE: For WatsonX Orchestrate integration with file uploads/downloads,
    use complete_risk_document_from_bytes instead, which accepts and returns bytes.

    This tool:
    1. Detects Q&A columns in each sheet using LLM
    2. Finds unanswered questions
    3. Generates answers using RAG (Retrieval-Augmented Generation)
    4. Fills the answers into the Excel file
    5. Formats the document professionally

    Args:
        input_file_path: Absolute path to the input Excel file (.xlsx)
        output_file_path: Optional absolute path for the output file.
                         If not provided, creates a file with '_completed' suffix.

    Returns:
        Success message with the output file path

    Example:
        complete_risk_document(
            input_file_path="/path/to/rfp_document.xlsx",
            output_file_path="/path/to/rfp_document_completed.xlsx"
        )
    """
    try:
        # Validate input file exists
        if not os.path.exists(input_file_path):
            return f"Error: Input file not found at {input_file_path}"

        # Validate file extension
        if not input_file_path.endswith('.xlsx'):
            return "Error: Input file must be an Excel file (.xlsx)"

        # Process the document
        logger.info(f"Processing document: {input_file_path}")
        result_path = process_document(input_file_path, output_file_path)

        return f"✓ Document processing complete! Output saved to: {result_path}"

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}", exc_info=True)
        return f"Error processing document: {str(e)}"


@mcp.tool()
def complete_risk_document_from_bytes(
    file_bytes: bytes,
    filename: str = "document.xlsx",
    return_as_bytes: bool = True
) -> Union[bytes, str]:
    """
    Process an Excel document from bytes and return the completed document.

    This tool is optimized for WatsonX Orchestrate integration where files
    are provided as bytes and the result should be returned as bytes for
    direct download.

    This tool:
    1. Accepts an Excel file as bytes (uploaded by user)
    2. Detects Q&A columns in each sheet using LLM
    3. Finds unanswered questions
    4. Generates answers using RAG (Retrieval-Augmented Generation)
    5. Fills the answers into the Excel file
    6. Returns the completed file as bytes (for download) or path

    Args:
        file_bytes: Excel file content as bytes
        filename: Original filename (used for extension detection, default: document.xlsx)
        return_as_bytes: If True, returns completed file as bytes. If False, returns file path.

    Returns:
        Completed Excel file as bytes (if return_as_bytes=True) or success message with path

    Example:
        # For WatsonX Orchestrate (returns bytes for download)
        completed_bytes = complete_risk_document_from_bytes(
            file_bytes=uploaded_file_bytes,
            filename="risk_assessment.xlsx",
            return_as_bytes=True
        )
    """
    input_temp_path = None
    output_temp_path = None

    try:
        # Validate file extension from filename
        if not filename.endswith('.xlsx'):
            if return_as_bytes:
                raise ValueError("Input file must be an Excel file (.xlsx)")
            return "Error: Input file must be an Excel file (.xlsx)"

        # Convert bytes to temporary file
        logger.info(f"Processing file from bytes: {filename}")
        input_temp_path = bytes_to_temp_file(file_bytes, filename)

        # Process the document
        logger.info(f"Processing document: {input_temp_path}")
        output_temp_path = process_document(input_temp_path)

        if return_as_bytes:
            # Read the completed file as bytes
            logger.info(f"Reading completed file as bytes: {output_temp_path}")
            result_bytes = file_to_bytes(output_temp_path)

            # Clean up temporary files
            cleanup_temp_file(input_temp_path)
            cleanup_temp_file(output_temp_path)

            return result_bytes
        else:
            # Return path (keep temp files for retrieval)
            return f"✓ Document processing complete! Temporary output saved to: {output_temp_path}"

    except Exception as e:
        # Clean up temporary files on error
        if input_temp_path:
            cleanup_temp_file(input_temp_path)
        if output_temp_path:
            cleanup_temp_file(output_temp_path)

        logger.error(f"Error processing document from bytes: {str(e)}", exc_info=True)

        if return_as_bytes:
            raise Exception(f"Error processing document: {str(e)}")
        return f"Error processing document: {str(e)}"


@mcp.tool()
def decode_base64_to_file(file_base64: str, output_path: str) -> str:
    """
    Decode a base64 string and save it as a file.

    Use this to convert the base64 result from complete_risk_document_base64
    back into a downloadable file.

    Args:
        file_base64: Base64-encoded file content
        output_path: Path where the file should be saved

    Returns:
        JSON with success status and file path
    """
    import json

    try:
        file_bytes = base64.b64decode(file_base64)

        with open(output_path, 'wb') as f:
            f.write(file_bytes)

        return json.dumps({
            "success": True,
            "message": "File saved successfully",
            "file_path": output_path,
            "file_size_bytes": len(file_bytes)
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Error decoding file: {str(e)}",
            "file_path": None
        })


@mcp.tool()
def encode_file_to_base64(file_path: str) -> str:
    """
    Encode a file to base64 string for transfer.

    Use this to convert an uploaded file to base64 before calling
    complete_risk_document_base64.

    Args:
        file_path: Path to the file to encode

    Returns:
        JSON with base64-encoded file content and metadata
    """
    import json

    try:
        if not os.path.exists(file_path):
            return json.dumps({
                "success": False,
                "message": f"File not found: {file_path}",
                "file_base64": None,
                "filename": None
            })

        with open(file_path, 'rb') as f:
            file_bytes = f.read()

        file_base64 = base64.b64encode(file_bytes).decode('utf-8')
        filename = os.path.basename(file_path)

        return json.dumps({
            "success": True,
            "message": "File encoded successfully",
            "file_base64": file_base64,
            "filename": filename,
            "file_size_bytes": len(file_bytes)
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Error encoding file: {str(e)}",
            "file_base64": None,
            "filename": None
        })


@mcp.tool()
def complete_risk_document_base64(
    file_base64: str,
    filename: str = "document.xlsx"
) -> str:
    """
    Process an Excel document from base64-encoded content and return completed document as base64.

    This tool is designed for WatsonX Orchestrate agentic workflows where files
    are uploaded and need to be passed as base64-encoded strings (since MCP protocol
    only supports JSON-serializable parameters).

    Workflow:
    1. User uploads Excel file to Orchestrate
    2. Orchestrate encodes file to base64 string
    3. Call this tool with the base64 string
    4. Tool returns JSON with completed file as base64
    5. Orchestrate decodes and returns file to user

    This tool:
    1. Decodes the base64 input to get the Excel file
    2. Detects Q&A columns in each sheet using LLM
    3. Finds unanswered questions
    4. Generates answers using RAG (Retrieval-Augmented Generation)
    5. Fills the answers into the Excel file
    6. Returns the completed file as base64

    Args:
        file_base64: Base64-encoded Excel file content (string)
        filename: Original filename for extension detection (default: document.xlsx)

    Returns:
        JSON string with:
        - success: boolean indicating if processing succeeded
        - message: status message
        - file_base64: base64-encoded completed Excel file (if successful)
        - filename: suggested filename for the completed file
        - file_size_bytes: size of the completed file

    Example:
        result = complete_risk_document_base64(
            file_base64="UEsDBBQABgAIAAAAIQ...",
            filename="risk_assessment.xlsx"
        )
    """
    import json

    input_temp_path = None
    output_temp_path = None

    try:
        # Validate file extension from filename
        if not filename.endswith('.xlsx'):
            return json.dumps({
                "success": False,
                "message": "Error: Input file must be an Excel file (.xlsx)",
                "file_base64": None,
                "filename": None,
                "file_size_bytes": 0
            })

        # Decode base64 to bytes
        logger.info(f"Decoding base64 file: {filename}")
        try:
            file_bytes = base64.b64decode(file_base64)
        except Exception as e:
            return json.dumps({
                "success": False,
                "message": f"Error: Invalid base64 encoding - {str(e)}",
                "file_base64": None,
                "filename": None,
                "file_size_bytes": 0
            })

        # Convert bytes to temporary file
        logger.info(f"Processing file from base64: {filename}")
        input_temp_path = bytes_to_temp_file(file_bytes, filename)

        # Process the document
        logger.info(f"Processing document: {input_temp_path}")
        output_temp_path = process_document(input_temp_path)

        # Read the completed file as bytes
        logger.info(f"Reading completed file: {output_temp_path}")
        result_bytes = file_to_bytes(output_temp_path)

        # Encode result to base64
        result_base64 = base64.b64encode(result_bytes).decode('utf-8')

        # Generate output filename
        from pathlib import Path
        input_path = Path(filename)
        output_filename = f"{input_path.stem}_completed{input_path.suffix}"

        # Clean up temporary files
        cleanup_temp_file(input_temp_path)
        cleanup_temp_file(output_temp_path)

        return json.dumps({
            "success": True,
            "message": "Document processing complete!",
            "file_base64": result_base64,
            "filename": output_filename,
            "file_size_bytes": len(result_bytes)
        })

    except Exception as e:
        # Clean up temporary files on error
        if input_temp_path:
            cleanup_temp_file(input_temp_path)
        if output_temp_path:
            cleanup_temp_file(output_temp_path)

        logger.error(f"Error processing document from base64: {str(e)}", exc_info=True)

        return json.dumps({
            "success": False,
            "message": f"Error processing document: {str(e)}",
            "file_base64": None,
            "filename": None,
            "file_size_bytes": 0
        })


@mcp.tool()
def detect_qa_columns(
    file_path: str,
    sheet_name: str
) -> str:
    """
    Detect which columns contain questions and answers in a specific Excel sheet.

    Uses LLM to analyze the spreadsheet structure and identify Q&A columns.

    Args:
        file_path: Absolute path to the Excel file
        sheet_name: Name of the sheet to analyze

    Returns:
        JSON-formatted string with detected column names or error message

    Example:
        detect_qa_columns(
            file_path="/path/to/document.xlsx",
            sheet_name="Risk Assessment"
        )
    """
    try:
        # Validate file exists
        if not os.path.exists(file_path):
            return f"Error: File not found at {file_path}"

        # Read the sheet
        df = pd.read_excel(file_path, sheet_name=sheet_name)

        if df.empty:
            return f"Error: Sheet '{sheet_name}' is empty"

        # Get model and detect columns
        model = get_model()
        question_col, answer_col = detect_qa_columns_in_sheet(df, model)

        if not question_col or not answer_col:
            return f"Error: Could not detect Q&A columns in sheet '{sheet_name}'"

        return f'{{"question_column": "{question_col}", "answer_column": "{answer_col}"}}'

    except Exception as e:
        logger.error(f"Error detecting columns: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"


@mcp.tool()
def answer_single_question(
    question: str,
    use_rag: bool = True,
    top_k: int = 5
) -> str:
    """
    Answer a single question using the LLM with optional RAG context.

    Useful for testing or answering individual questions outside of document processing.

    Args:
        question: The question to answer
        use_rag: Whether to use RAG (Retrieval-Augmented Generation) for context
        top_k: Number of similar examples to retrieve if using RAG

    Returns:
        Generated answer to the question

    Example:
        answer_single_question(
            question="What is IBM's data retention policy?",
            use_rag=True,
            top_k=5
        )
    """
    try:
        model = get_model()

        if use_rag:
            answer = ask_llm(question, model)
        else:
            # Direct answer without RAG context
            messages = [
                {
                    "role": "system",
                    "content": "You are a professional document completion assistant for IBM. Answer questions directly and professionally."
                },
                {
                    "role": "user",
                    "content": question
                }
            ]
            response = model.chat(messages=messages)
            answer = response["choices"][0]["message"]["content"]

        return answer

    except Exception as e:
        logger.error(f"Error answering question: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"


@mcp.tool()
def search_knowledge_base(
    query: str,
    top_k: int = 5,
    similarity_threshold: float = 0.5
) -> str:
    """
    Search the knowledge base for relevant Q&A examples.

    Retrieves similar questions and answers from the AstraDB vector database.
    Useful for understanding what information is available before processing documents.

    Args:
        query: Search query or question
        top_k: Maximum number of results to return
        similarity_threshold: Minimum similarity score (0.0 to 1.0)

    Returns:
        Formatted string with relevant Q&A examples

    Example:
        search_knowledge_base(
            query="security compliance requirements",
            top_k=5,
            similarity_threshold=0.5
        )
    """
    try:
        context = get_relevant_context(query, top_k, similarity_threshold)

        if not context or context.startswith("No relevant examples"):
            return f"No relevant examples found for query: '{query}'"

        return f"Found relevant examples:\n\n{context}"

    except Exception as e:
        logger.error(f"Error searching knowledge base: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"


@mcp.tool()
def list_excel_sheets(file_path: str) -> str:
    """
    List all sheet names in an Excel workbook.

    Helpful for understanding document structure before processing.

    Args:
        file_path: Absolute path to the Excel file

    Returns:
        JSON-formatted list of sheet names or error message

    Example:
        list_excel_sheets(file_path="/path/to/document.xlsx")
    """
    try:
        # Validate file exists
        if not os.path.exists(file_path):
            return f"Error: File not found at {file_path}"

        # Get sheet names
        import openpyxl
        wb = openpyxl.load_workbook(file_path, read_only=True)
        sheet_names = wb.sheetnames
        wb.close()

        return f'{{"sheets": {sheet_names}, "total_count": {len(sheet_names)}}}'

    except Exception as e:
        logger.error(f"Error listing sheets: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"


@mcp.tool()
def health_check() -> str:
    """Health check endpoint for container orchestration"""
    import json
    return json.dumps({
        "status": "healthy",
        "service": "risk-document-completion",
        "version": "1.0.0"
    })


def main():
    """Entry point for the MCP server"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Risk Document Completion MCP Server')
    parser.add_argument('--transport', choices=['stdio', 'http'], default='stdio',
                       help='Transport protocol (stdio or http)')
    parser.add_argument('--port', type=int, default=8080,
                       help='Port for HTTP transport')
    parser.add_argument('--host', default='0.0.0.0',
                       help='Host for HTTP transport')
    
    args = parser.parse_args()
    
    logger.info(f"Starting Risk Document Completion MCP Server...")
    logger.info(f"Transport: {args.transport}")
    
    if args.transport == 'http':
        logger.info(f"HTTP server listening on {args.host}:{args.port}")
        mcp.run(transport='http', host=args.host, port=args.port)
    else:
        logger.info("Using stdio transport")
        mcp.run()


if __name__ == "__main__":
    main()
