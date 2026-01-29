#!/usr/bin/env python3
"""
Test script to decode base64 string using the orchestrate_decode_file tool
"""

from orchestrate_decode_file import decode_base64_to_file

# Read the base64 string from the file
with open('decode_string.txt', 'r') as f:
    base64_string = f.read().strip()

print("Decoding base64 string...")
print(f"Input length: {len(base64_string)} characters")

# Call the decoder tool
result_bytes = decode_base64_to_file(base64_string)

# Save the decoded file
output_path = 'decoded_output.xlsx'
with open(output_path, 'wb') as f:
    f.write(result_bytes)

print(f"✓ Successfully decoded and saved to: {output_path}")
print(f"Output size: {len(result_bytes)} bytes")
