# Cloud Object Storage Solution (Recommended Architecture)

## Why Cloud Storage is Better

### Current Base64 Approach (Limitations)

❌ **Size Limits:** Base64 increases file size by 33%, hitting message size limits  
❌ **Memory Issues:** Large files (>10MB) cause memory problems  
❌ **Performance:** Encoding/decoding adds latency  
❌ **Network Overhead:** Passing large strings through multiple tools  
❌ **Complexity:** Three-tool chain with multiple conversions  

### Cloud Storage Approach (Benefits)

✅ **No Size Limits:** Handle files of any size  
✅ **Efficient:** Direct file access, no encoding overhead  
✅ **Simpler:** Two-tool workflow instead of three  
✅ **Scalable:** Cloud storage handles concurrency  
✅ **Secure:** Built-in access controls and encryption  
✅ **Persistent:** Files available for audit/review  

## Architecture Comparison

### Current (Base64)
```
User Upload → Encode (base64) → MCP Process → Decode → Download
              ↓ 33% larger    ↓ memory      ↓ overhead
```

### Recommended (Cloud Storage)
```
User Upload → Upload to COS → MCP Process (reads from COS) → Download from COS
              ↓ fast         ↓ efficient   ↓ direct access
```

## Implementation: Cloud Object Storage Solution

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│              CLOUD STORAGE WORKFLOW                             │
└─────────────────────────────────────────────────────────────────┘

1. User uploads Excel file in Orchestrate chat
         ↓
2. Python Tool: upload_to_cloud_storage
   - Input: file_bytes from Orchestrate
   - Output: file_url (COS URL)
         ↓
3. MCP Tool: complete_risk_document_from_url
   - Input: file_url
   - Downloads from COS
   - Processes document
   - Uploads result to COS
   - Output: result_url
         ↓
4. User downloads from result_url
   (or Orchestrate auto-downloads)
```

### Benefits of This Approach

1. **No Encoding Overhead:** Files stay as binary, no base64 conversion
2. **Unlimited Size:** COS handles files up to 5TB
3. **Better Performance:** Direct file I/O instead of string manipulation
4. **Simpler Code:** Fewer conversions, cleaner logic
5. **Audit Trail:** Files persist in COS for compliance
6. **Concurrent Access:** Multiple users can process simultaneously

## Implementation Code

### Tool 1: Upload to Cloud Storage (Python Tool)

```python
#!/usr/bin/env python3
"""
Upload file to IBM Cloud Object Storage
"""
import ibm_boto3
from ibm_botocore.client import Config
from ibm_watsonx_orchestrate.agent_builder.tools import tool
import os
from datetime import datetime
import uuid

# COS Configuration
COS_ENDPOINT = os.getenv('COS_ENDPOINT', 'https://s3.us-south.cloud-object-storage.appdomain.cloud')
COS_API_KEY = os.getenv('COS_API_KEY')
COS_INSTANCE_CRN = os.getenv('COS_INSTANCE_CRN')
COS_BUCKET = os.getenv('COS_BUCKET', 'risk-documents')

def get_cos_client():
    """Initialize COS client"""
    return ibm_boto3.client(
        's3',
        ibm_api_key_id=COS_API_KEY,
        ibm_service_instance_id=COS_INSTANCE_CRN,
        config=Config(signature_version='oauth'),
        endpoint_url=COS_ENDPOINT
    )

@tool()
def upload_file_to_storage(
    file_bytes: bytes,
    filename: str = "document.xlsx"
) -> str:
    """Upload file to cloud storage and return URL.
    
    Args:
        file_bytes: File content from Orchestrate upload
        filename: Original filename
        
    Returns:
        str: JSON with file URL and metadata
    """
    import json
    
    try:
        # Validate file
        if not filename.endswith('.xlsx'):
            raise ValueError("File must be Excel (.xlsx)")
        
        # Generate unique key
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        object_key = f"uploads/{timestamp}_{unique_id}_{filename}"
        
        # Upload to COS
        cos_client = get_cos_client()
        cos_client.put_object(
            Bucket=COS_BUCKET,
            Key=object_key,
            Body=file_bytes,
            ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Generate presigned URL (valid for 1 hour)
        file_url = cos_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': COS_BUCKET, 'Key': object_key},
            ExpiresIn=3600
        )
        
        return json.dumps({
            "success": True,
            "file_url": file_url,
            "object_key": object_key,
            "filename": filename,
            "file_size_bytes": len(file_bytes)
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })
```

### Tool 2: MCP Tool with Cloud Storage

```python
#!/usr/bin/env python3
"""
MCP Tool: Process document from Cloud Object Storage
"""
import os
import logging
import tempfile
import requests
import ibm_boto3
from ibm_botocore.client import Config
from mcp.server.fastmcp import FastMCP
from auto_complete_document import process_document

logger = logging.getLogger(__name__)
mcp = FastMCP("risk-document-completion")

# COS Configuration
COS_ENDPOINT = os.getenv('COS_ENDPOINT')
COS_API_KEY = os.getenv('COS_API_KEY')
COS_INSTANCE_CRN = os.getenv('COS_INSTANCE_CRN')
COS_BUCKET = os.getenv('COS_BUCKET', 'risk-documents')

def get_cos_client():
    """Initialize COS client"""
    return ibm_boto3.client(
        's3',
        ibm_api_key_id=COS_API_KEY,
        ibm_service_instance_id=COS_INSTANCE_CRN,
        config=Config(signature_version='oauth'),
        endpoint_url=COS_ENDPOINT
    )

@mcp.tool()
def complete_risk_document_from_url(
    file_url: str,
    filename: str = "document.xlsx"
) -> str:
    """
    Process Excel document from Cloud Object Storage URL.
    
    This tool:
    1. Downloads file from COS using URL
    2. Processes document with RAG
    3. Uploads completed file to COS
    4. Returns URL to download completed file
    
    Args:
        file_url: URL to download input file from COS
        filename: Original filename
        
    Returns:
        JSON with completed file URL and metadata
    """
    import json
    from datetime import datetime
    import uuid
    
    input_temp_path = None
    output_temp_path = None
    
    try:
        # Download file from URL
        logger.info(f"Downloading file from: {file_url}")
        response = requests.get(file_url, timeout=60)
        response.raise_for_status()
        
        # Save to temporary file
        suffix = os.path.splitext(filename)[1] or '.xlsx'
        input_temp_path = tempfile.NamedTemporaryFile(
            mode='wb',
            suffix=suffix,
            delete=False
        ).name
        
        with open(input_temp_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"File downloaded to: {input_temp_path}")
        
        # Process document
        logger.info("Processing document...")
        output_temp_path = process_document(input_temp_path)
        logger.info(f"Document processed: {output_temp_path}")
        
        # Upload result to COS
        cos_client = get_cos_client()
        
        # Generate unique key for output
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        base_name = os.path.splitext(filename)[0]
        output_key = f"completed/{timestamp}_{unique_id}_{base_name}_completed.xlsx"
        
        # Upload completed file
        with open(output_temp_path, 'rb') as f:
            cos_client.put_object(
                Bucket=COS_BUCKET,
                Key=output_key,
                Body=f,
                ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        
        logger.info(f"Completed file uploaded to COS: {output_key}")
        
        # Generate presigned URL for download (valid for 24 hours)
        result_url = cos_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': COS_BUCKET, 'Key': output_key},
            ExpiresIn=86400  # 24 hours
        )
        
        # Get file size
        file_size = os.path.getsize(output_temp_path)
        
        # Cleanup temp files
        os.unlink(input_temp_path)
        os.unlink(output_temp_path)
        
        return json.dumps({
            "success": True,
            "message": "Document processing complete!",
            "result_url": result_url,
            "object_key": output_key,
            "filename": f"{base_name}_completed.xlsx",
            "file_size_bytes": file_size
        })
        
    except Exception as e:
        # Cleanup on error
        if input_temp_path and os.path.exists(input_temp_path):
            os.unlink(input_temp_path)
        if output_temp_path and os.path.exists(output_temp_path):
            os.unlink(output_temp_path)
        
        logger.error(f"Error processing document: {str(e)}", exc_info=True)
        
        return json.dumps({
            "success": False,
            "message": f"Error: {str(e)}",
            "result_url": None
        })
```

### Orchestrate Skill Definition

```yaml
name: "Complete Risk Questionnaire (Cloud Storage)"
description: "Auto-fill questionnaires using cloud storage"

inputs:
  - name: uploaded_file
    type: file
    required: true

steps:
  # Step 1: Upload to Cloud Object Storage
  - name: upload
    tool: upload_file_to_storage
    inputs:
      file_bytes: "{{ inputs.uploaded_file.content }}"
      filename: "{{ inputs.uploaded_file.name }}"
    outputs:
      - file_url
      - object_key

  # Step 2: Process with MCP (reads from COS, writes to COS)
  - name: process
    tool: complete_risk_document_from_url
    inputs:
      file_url: "{{ json_parse(steps.upload.outputs).file_url }}"
      filename: "{{ inputs.uploaded_file.name }}"
    outputs:
      - result_url
      - filename
      - message

outputs:
  - name: download_url
    value: "{{ json_parse(steps.process.outputs).result_url }}"
    type: url
    description: "Click to download completed document"
  - name: status
    value: "{{ json_parse(steps.process.outputs).message }}"
    type: string
```

## Environment Configuration

### Required Environment Variables

```bash
# IBM Cloud Object Storage
export COS_ENDPOINT="https://s3.us-south.cloud-object-storage.appdomain.cloud"
export COS_API_KEY="your-cos-api-key"
export COS_INSTANCE_CRN="crn:v1:bluemix:public:cloud-object-storage:..."
export COS_BUCKET="risk-documents"

# WatsonX AI (existing)
export WATSONX_API_KEY="your-watsonx-key"
export WATSONX_PROJECT_ID="your-project-id"

# AstraDB (existing)
export ASTRA_DB_TOKEN="your-astra-token"
export ASTRA_DB_ENDPOINT="your-astra-endpoint"
```

### COS Bucket Setup

```bash
# Create bucket (one-time setup)
ibmcloud cos bucket-create \
  --bucket risk-documents \
  --ibm-service-instance-id $COS_INSTANCE_CRN \
  --region us-south

# Set CORS policy (allow Orchestrate access)
ibmcloud cos bucket-cors-put \
  --bucket risk-documents \
  --cors-configuration file://cors-config.json
```

**cors-config.json:**
```json
{
  "CORSRules": [
    {
      "AllowedOrigins": ["https://*.watsonx.ibm.com"],
      "AllowedMethods": ["GET", "PUT", "POST"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3600
    }
  ]
}
```

## Comparison: Base64 vs Cloud Storage

| Aspect | Base64 Approach | Cloud Storage Approach |
|--------|----------------|----------------------|
| **File Size Limit** | ~10MB (message limits) | Unlimited (5TB+) |
| **Performance** | Slow (encoding overhead) | Fast (direct I/O) |
| **Memory Usage** | High (entire file in memory) | Low (streaming) |
| **Complexity** | 3 tools, multiple conversions | 2 tools, direct access |
| **Scalability** | Limited (memory bound) | Excellent (cloud native) |
| **Cost** | Free (but limited) | ~$0.023/GB/month |
| **Audit Trail** | None (ephemeral) | Full (persistent) |
| **Security** | Basic | Enterprise (IAM, encryption) |
| **Concurrent Users** | Limited | Unlimited |

## Migration Path

### Phase 1: Keep Base64 for Small Files
- Use base64 approach for files <5MB
- Quick to implement, no infrastructure changes

### Phase 2: Add Cloud Storage for Large Files
- Implement cloud storage tools
- Route large files (>5MB) to cloud storage
- Keep base64 for small files

### Phase 3: Full Cloud Storage Migration
- Migrate all file handling to cloud storage
- Deprecate base64 tools
- Simplify architecture

## Cost Analysis

### Base64 Approach
- **Infrastructure:** Free (uses existing compute)
- **Limitations:** File size, performance, scalability

### Cloud Storage Approach
- **Storage:** $0.023/GB/month (IBM COS Standard)
- **Requests:** $0.005 per 1,000 PUT requests
- **Transfer:** Free within IBM Cloud
- **Example:** 1,000 documents/month (50MB each) = ~$1.15/month

**ROI:** Better performance, scalability, and user experience far outweigh minimal cost.

## Security Considerations

### Cloud Storage Benefits
- **Encryption at Rest:** AES-256 encryption
- **Encryption in Transit:** TLS 1.2+
- **Access Control:** IAM policies, presigned URLs
- **Audit Logging:** Full activity logs
- **Compliance:** SOC 2, ISO 27001, GDPR

### Implementation
```python
# Presigned URLs with expiration
url = cos_client.generate_presigned_url(
    'get_object',
    Params={'Bucket': bucket, 'Key': key},
    ExpiresIn=3600  # 1 hour
)

# Server-side encryption
cos_client.put_object(
    Bucket=bucket,
    Key=key,
    Body=file_bytes,
    ServerSideEncryption='AES256'
)
```

## Recommendation

**Use Cloud Object Storage** for production deployments:

✅ **Better Performance:** No encoding overhead  
✅ **Unlimited Scale:** Handle any file size  
✅ **Simpler Code:** Fewer tools, cleaner logic  
✅ **Enterprise Ready:** Security, audit, compliance  
✅ **Cost Effective:** Minimal cost for huge benefits  

**Use Base64** only for:
- Quick prototypes/demos
- Very small files (<1MB)
- Environments without cloud storage access

## Next Steps

1. Set up IBM Cloud Object Storage bucket
2. Configure environment variables
3. Implement upload tool (Python)
4. Update MCP tool to use COS
5. Create Orchestrate skill
6. Test with sample files
7. Monitor performance and costs

## References

- [IBM Cloud Object Storage Documentation](https://cloud.ibm.com/docs/cloud-object-storage)
- [IBM COS Python SDK](https://github.com/IBM/ibm-cos-sdk-python)
- [Presigned URLs Guide](https://cloud.ibm.com/docs/cloud-object-storage?topic=cloud-object-storage-presign-url)
- [Base64 Solution](ORCHESTRATE_FILE_HANDLING_SOLUTION.md) (current approach)