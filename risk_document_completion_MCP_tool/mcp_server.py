#!/usr/bin/env python3
"""
Risk Document Completion MCP Server
Exposes document completion functionality as MCP tools for WatsonX Orchestrate
"""

import os
import logging
from typing import Optional

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


@mcp.tool()
def complete_risk_document(
    input_file_path: str,
    output_file_path: Optional[str] = None
) -> str:
    """
    Process an Excel document and automatically fill in unanswered questions using RAG.

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


def main():
    """Entry point for the MCP server"""
    logger.info("Starting Risk Document Completion MCP Server...")
    mcp.run()


if __name__ == "__main__":
    main()
