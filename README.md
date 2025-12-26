# Risk Document Completion MCP Tool

Automatically detects Q&A columns in Excel sheets and fills in answers using RAG (Retrieval-Augmented Generation).

## Features

- **Automatic Column Detection**: Uses LLM to identify which columns contain questions and answers in each sheet
- **RAG-Based Answering**: Retrieves relevant context from AstraDB vector database to generate accurate answers
- **Multi-Sheet Support**: Processes all sheets in an Excel workbook
- **Smart Cell Handling**: Automatically unmerges cells when needed
- **Professional Formatting**: Proper cell alignment, row heights, and column widths

## Workflow

1. **Initialize Model** - Sets up the LLM for both column detection and question answering
2. **Iterate Through Each Sheet** - Processes every sheet in the workbook
3. **Detect Q&A Columns** - Uses LLM to identify which columns have questions and answers
4. **Answer Questions** - For each unanswered question:
   - Uses RAG to retrieve context from AstraDB
   - Generates answer using the LLM
   - Fills it into the document
5. **Save Document** - Returns completed document to user

## Requirements

- Python 3.8+
- IBM WatsonX AI credentials
- AstraDB database with vector search enabled

## Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install pandas openpyxl ibm-watsonx-ai python-dotenv astrapy sentence-transformers
```

## Environment Variables

Create a `.env` file with the following:

```env
MODEL_URL=<your_watsonx_url>
API_KEY=<your_api_key>
PROJECT_ID=<your_project_id>
SPACE_ID=<your_space_id>
MODEL=<model_id>
ASTRA_DB_API_ENDPOINT=<your_astra_endpoint>
ASTRA_DB_APPLICATION_TOKEN=<your_astra_token>
```

## Usage

```bash
# Basic usage
python auto_complete_document.py input_file.xlsx

# Specify output file
python auto_complete_document.py input_file.xlsx output_file.xlsx
```

## License

MIT
