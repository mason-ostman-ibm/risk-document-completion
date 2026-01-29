#!/usr/bin/env python3
"""
Orchestrate File Decoder Tool
Converts base64 output from MCP tool back to downloadable Excel file
"""

import base64
from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool()
def decode_base64_to_file(file_base64: str) -> bytes:
    """Decode base64 string and return as downloadable Excel file.

    This tool converts the base64-encoded output from the complete_risk_document_base64
    MCP tool back into a downloadable Excel file that can be provided to the user.

    Args:
        file_base64 (str): Base64-encoded file content from MCP tool

    Returns:
        bytes: The decoded Excel file content as bytes for download
    """
    # Decode base64 to bytes
    file_bytes = base64.b64decode(file_base64)

    # Return the bytes directly - Orchestrate will handle the download
    return file_bytes
