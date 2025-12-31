import pandas as pd
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
import os
from dotenv import load_dotenv

load_dotenv()

def initialize_model():
    print("Setting up credentials...")
    credentials = Credentials(
        url=os.getenv("MODEL_URL"),
        username="mason.ostman@ibm.com",
        api_key=os.getenv("API_KEY")
    )

    project_id = os.getenv("PROJECT_ID")
    space_id = os.getenv("SPACE_ID")
    model_id = os.getenv("MODEL")

    print(f"Model ID: {model_id}")
    print(f"Project ID: {project_id}")

    parameters = {
        "max_new_tokens": 2000,
        "temperature": 0,
        "top_p": 1
    }

    print("Initializing model...")
    model = ModelInference(
        model_id=model_id,
        params=parameters,
        credentials=credentials,
        project_id=project_id,
        space_id=space_id
    )
    print("Model initialized!\n")

    return model

def detect_qa_columns(file_path, sheet_number=0, model=None):
    if model is None:
        model = initialize_model()

    print(f"Reading Excel file: {file_path}, sheet: {sheet_number}")
    df = pd.read_excel(file_path, sheet_name=sheet_number)
    print(f"File loaded. Shape: {df.shape}")

    sample_data = df.head(5).to_string()
    print(f"Sample data:\n{sample_data}\n")

    prompt = f"""Given this spreadsheet data, identify which column contains questions and which contains answers.

{sample_data}

Respond in this exact format:
Question column: [column name]
Answer column: [column name]"""

    print("Sending request to LLM...")

    messages = [
        {
            "role": "user",
            "content": prompt
        }
    ]

    response = model.chat(messages=messages)
    print("Response received!")
    print(f"Response type: {type(response)}")
    print(f"Full response: {response}")

    answer = response["choices"][0]["message"]["content"]
    print(f"\nExtracted answer:\n{answer}")
    return answer


if __name__ == "__main__":
    result = detect_qa_columns("RFP_Supplier_overview.xlsx", sheet_number=0)