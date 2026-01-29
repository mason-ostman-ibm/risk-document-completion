#!/usr/bin/env python3
"""
Orchestrate File Encoder Tool
Converts uploaded Excel files to base64 for MCP tool input
"""

import base64
from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool()
def encode_file_to_base64(file_bytes: bytes, filename: str = "document.xlsx") -> str:
    """Encode an Excel file to base64 string for MCP tool processing.

    This tool converts an uploaded Excel file (received as bytes) into a
    base64-encoded string that can be passed to the complete_risk_document_base64 MCP tool.

    Args:
        file_bytes (bytes): The uploaded Excel file content as bytes
        filename (str): Original filename for validation (default: "document.xlsx")

    Returns:
        str: Base64-encoded file content (returns just the string, not JSON)
    """
    # Validate file content
    if not file_bytes or len(file_bytes) == 0:
        raise ValueError("File content is empty")

    # Validate file extension
    if not filename.endswith('.xlsx'):
        raise ValueError("File must be an Excel file (.xlsx)")

    # Encode file bytes to base64 and return just the string
    file_base64 = base64.b64encode(file_bytes).decode('utf-8')

    return file_base64
