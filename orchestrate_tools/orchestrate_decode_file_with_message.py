#!/usr/bin/env python3
"""
Orchestrate File Decoder Tool - Alternative Version
Converts base64 to file and provides clear instructions
"""

import base64
import json
from ibm_watsonx_orchestrate.agent_builder.tools import tool


@tool()
def decode_base64_to_file_with_message(file_base64: str, filename: str = "completed_document.xlsx") -> str:
    """Decode base64 string and provide download instructions.

    This tool converts the base64-encoded output from the complete_risk_document_base64
    MCP tool and provides it in a user-friendly format.

    Args:
        file_base64 (str): Base64-encoded file content from MCP tool
        filename (str): Desired filename for the output (default: "completed_document.xlsx")

    Returns:
        str: Message with file details and the base64 content for download
    """
    try:
        # Decode base64 to bytes to validate and get size
        file_bytes = base64.b64decode(file_base64)
        file_size_mb = len(file_bytes) / (1024 * 1024)

        # Return a formatted message with the base64
        return f"""✅ Document processing complete!

**File Details:**
- Filename: {filename}
- Size: {file_size_mb:.2f} MB
- Format: Excel (.xlsx)

**Download Instructions:**
The completed file is ready for download. The system will provide a download link for you.

Note: If the downloaded file shows as 'output.octet-stream', please rename it to '{filename}' after downloading.
"""

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Error decoding file: {str(e)}"
        })
