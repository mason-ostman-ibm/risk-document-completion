# Testing Guide - Risk Document Completion

This guide shows you how to test the document completion functionality before deploying to production.

## Quick Test (Automated)

The easiest way to test is using the automated test script:

```bash
# Option 1: Create a sample document and test it automatically
python test_document_completion.py

# Option 2: Test with your own document
python test_document_completion.py /path/to/your/document.xlsx
```

This will run all three test scenarios:
1. File-based completion (original method)
2. Bytes-based completion (Orchestrate method)
3. Individual tool tests

## Manual Testing Options

### Option 1: Quick Python Test (Recommended for First Test)

```python
# test_quick.py
from mcp_server import complete_risk_document_from_bytes
import os

# Read your test file
test_file = "your_test_document.xlsx"
with open(test_file, 'rb') as f:
    file_bytes = f.read()

print(f"Processing {len(file_bytes)} bytes...")

# Process the document
try:
    result_bytes = complete_risk_document_from_bytes(
        file_bytes=file_bytes,
        filename=test_file,
        return_as_bytes=True
    )

    # Save the result
    output_file = test_file.replace('.xlsx', '_completed.xlsx')
    with open(output_file, 'wb') as f:
        f.write(result_bytes)

    print(f"✅ Success! Output saved to: {output_file}")
    print(f"Output size: {len(result_bytes)} bytes")

except Exception as e:
    print(f"❌ Error: {e}")
```

Run it:
```bash
python test_quick.py
```

### Option 2: Interactive Python Session

```bash
python3
```

```python
# Import the function
from mcp_server import complete_risk_document

# Test with a file path
result = complete_risk_document(
    input_file_path="/path/to/your/test.xlsx",
    output_file_path="/path/to/output.xlsx"
)

print(result)
```

### Option 3: Test Individual Tools

```python
from mcp_server import (
    list_excel_sheets,
    detect_qa_columns,
    answer_single_question,
    search_knowledge_base
)

# List sheets in your document
sheets = list_excel_sheets("/path/to/document.xlsx")
print("Sheets:", sheets)

# Detect Q&A columns in a specific sheet
columns = detect_qa_columns(
    file_path="/path/to/document.xlsx",
    sheet_name="Risk Assessment"
)
print("Detected columns:", columns)

# Test answering a single question
answer = answer_single_question(
    question="What is IBM's data retention policy?",
    use_rag=True
)
print("Answer:", answer)

# Search the knowledge base
results = search_knowledge_base(
    query="security compliance",
    top_k=3
)
print("Search results:", results)
```

## Creating a Test Document

If you don't have a test document, create one:

### Option 1: Use the Test Script

```bash
python test_document_completion.py
# This creates test_rfp.xlsx automatically
```

### Option 2: Create Manually in Excel

1. Open Excel
2. Create a new workbook
3. Add two columns: "Question" and "Response"
4. Add some questions:
   ```
   Question                              | Response
   --------------------------------------|----------
   What is your company name?            | IBM
   Describe your security practices.     |
   What certifications do you hold?      |
   Do you comply with GDPR?              | Yes
   What is your incident response time?  |
   ```
5. Leave some responses blank (these will be filled by AI)
6. Save as `test_rfp.xlsx`

### Option 3: Create Programmatically

```python
import pandas as pd

data = {
    'Question': [
        'What is your company name?',
        'Describe your data encryption practices.',
        'What is your incident response time?',
        'Do you comply with GDPR?',
        'What certifications do you hold?',
    ],
    'Response': [
        'IBM Corporation',  # Answered (will be skipped)
        '',                 # Unanswered (will be filled)
        '',                 # Unanswered (will be filled)
        'Yes',              # Answered (will be skipped)
        '',                 # Unanswered (will be filled)
    ]
}

df = pd.DataFrame(data)
df.to_excel('test_rfp.xlsx', sheet_name='Security Assessment', index=False)
print("✅ Test document created: test_rfp.xlsx")
```

## Testing the Bytes-Based Function (Orchestrate Simulation)

This simulates how WatsonX Orchestrate will use the tool:

```python
from mcp_server import complete_risk_document_from_bytes

# 1. Read file as bytes (simulates user upload)
with open('test_rfp.xlsx', 'rb') as f:
    uploaded_bytes = f.read()

print(f"User uploaded: {len(uploaded_bytes)} bytes")

# 2. Process the document (this happens on the server)
completed_bytes = complete_risk_document_from_bytes(
    file_bytes=uploaded_bytes,
    filename="test_rfp.xlsx",
    return_as_bytes=True
)

print(f"Server returned: {len(completed_bytes)} bytes")

# 3. Save for download (simulates user download)
with open('test_rfp_completed.xlsx', 'wb') as f:
    f.write(completed_bytes)

print("✅ User downloaded: test_rfp_completed.xlsx")
```

## Expected Output

When you run the test, you should see:

```
============================================================
AUTO COMPLETE DOCUMENT TOOL
============================================================

Initializing LLM model...
Model initialized!

Loading workbook: test_rfp.xlsx
Found 1 sheets

============================================================
Processing sheet: Security Assessment
============================================================
  Detecting Q&A columns...
  ✓ Question column: Question
  ✓ Answer column: Response
  Answering row 3: Describe your data encryption practices...
  Answering row 4: What is your incident response time?...
  Answering row 6: What certifications do you hold?...
  ✓ Answered 3 questions in this sheet

============================================================
PROCESSING SUMMARY
============================================================
Sheets processed: 1/1
Total questions answered: 3
Output file: test_rfp_completed.xlsx
============================================================
```

## Verifying the Results

After processing, open the completed Excel file and verify:

1. **Previously answered questions remain unchanged**
   - "IBM Corporation" should still be there
   - "Yes" should still be there

2. **Previously blank answers are now filled**
   - Security practices question should have a detailed answer
   - Incident response time should have a reasonable answer
   - Certifications should list relevant IBM certifications

3. **Formatting is preserved**
   - Column widths should be appropriate
   - Text should wrap properly
   - Row heights should accommodate the content

## Testing Specific Features

### Test 1: Column Detection

```python
from mcp_server import detect_qa_columns
import pandas as pd

# Test with your document
result = detect_qa_columns(
    file_path="test_rfp.xlsx",
    sheet_name="Security Assessment"
)

print("Detected columns:", result)
# Expected: {"question_column": "Question", "answer_column": "Response"}
```

### Test 2: RAG (Retrieval-Augmented Generation)

```python
from mcp_server import search_knowledge_base

# Search for relevant Q&A examples
results = search_knowledge_base(
    query="data encryption security",
    top_k=5,
    similarity_threshold=0.5
)

print("Found examples:")
print(results)
```

### Test 3: Answer Quality

```python
from mcp_server import answer_single_question

# Test with RAG
answer_with_rag = answer_single_question(
    question="What encryption standards does IBM use?",
    use_rag=True
)

# Test without RAG
answer_without_rag = answer_single_question(
    question="What encryption standards does IBM use?",
    use_rag=False
)

print("With RAG:", answer_with_rag)
print("\nWithout RAG:", answer_without_rag)
```

## Troubleshooting

### Issue: "Module not found"

```bash
# Make sure you're in the right directory
cd /path/to/risk_document_completion_MCP_tool

# Install dependencies
pip install -r requirements.txt
```

### Issue: "Model initialization failed"

```bash
# Check environment variables
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('MODEL_URL:', os.getenv('MODEL_URL'))"

# Verify .env file exists
ls -la .env
```

### Issue: "Collection not found" (AstraDB error)

```python
# Test AstraDB connection
from dotenv import load_dotenv
import os
from astrapy import DataAPIClient

load_dotenv()
client = DataAPIClient(os.getenv('ASTRA_DB_APPLICATION_TOKEN'))
db = client.get_database(os.getenv('ASTRA_DB_API_ENDPOINT'))
print('Collections:', db.list_collection_names())
# Should include 'qa_collection'
```

### Issue: "No relevant examples found"

This is normal if your AstraDB collection is empty or doesn't have relevant examples. The tool will still work, but answers will be based on the model's general knowledge rather than specific examples.

To add examples to your knowledge base, see the documentation on populating AstraDB.

### Issue: Answers are low quality

Check:
1. Is RAG enabled? (`use_rag=True`)
2. Does your AstraDB collection have relevant Q&A examples?
3. Is the similarity threshold too high? (try lowering from 0.5 to 0.3)

## Performance Benchmarks

Expected processing times:

- **First request**: 2-3 seconds (model initialization)
- **Subsequent requests**:
  - Column detection: < 1 second
  - Per question: 2-3 seconds
  - RAG query: < 100ms
- **Complete document (10 questions)**: ~20-30 seconds

## Testing in WatsonX Orchestrate

Once you've verified the tool works locally, test in Orchestrate:

1. Deploy to Code Engine (see ORCHESTRATE_INTEGRATION.md)
2. Register the tool in Orchestrate
3. Create a test flow with file upload/download
4. Upload your test document
5. Verify the completed document downloads correctly

## Automated CI/CD Testing

For production deployments, add to your CI/CD pipeline:

```yaml
# .github/workflows/test.yml
name: Test Document Completion

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        env:
          MODEL_URL: ${{ secrets.MODEL_URL }}
          API_KEY: ${{ secrets.API_KEY }}
          PROJECT_ID: ${{ secrets.PROJECT_ID }}
          SPACE_ID: ${{ secrets.SPACE_ID }}
          MODEL: ${{ secrets.MODEL }}
          ASTRA_DB_API_ENDPOINT: ${{ secrets.ASTRA_DB_API_ENDPOINT }}
          ASTRA_DB_APPLICATION_TOKEN: ${{ secrets.ASTRA_DB_APPLICATION_TOKEN }}
        run: python test_document_completion.py
```

## Next Steps

After successful testing:

1. ✅ Local tests pass
2. ✅ Answer quality is acceptable
3. ✅ Performance is acceptable
4. → Deploy to IBM Code Engine (see ORCHESTRATE_INTEGRATION.md)
5. → Register with WatsonX Orchestrate
6. → Test end-to-end in Orchestrate
7. → Share with users

## Support

For issues during testing:
- Check the error messages carefully
- Verify environment variables are set
- Test components individually (RAG, LLM, file handling)
- Review logs in mcp_server.py (logger output)
