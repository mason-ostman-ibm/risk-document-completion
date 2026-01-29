#!/usr/bin/env python3
"""
Demo script showing how to use MCP tools directly
without needing to make HTTP requests
"""

from mcp_server import (
    answer_single_question,
    search_knowledge_base,
    list_excel_sheets,
    get_model
)

def demo_answer_question():
    """Demo answering a single question with RAG"""
    print("=" * 60)
    print("Demo: Answering a Single Question")
    print("=" * 60)

    question = "What is IBM's approach to data security?"
    print(f"\nQuestion: {question}")
    print("\nGenerating answer with RAG...")

    try:
        answer = answer_single_question(
            question=question,
            use_rag=True,
            top_k=5
        )
        print(f"\nAnswer:\n{answer}")
    except Exception as e:
        print(f"\nError: {e}")

    print("\n" + "=" * 60 + "\n")

def demo_search_knowledge_base():
    """Demo searching the knowledge base"""
    print("=" * 60)
    print("Demo: Searching Knowledge Base")
    print("=" * 60)

    query = "compliance requirements"
    print(f"\nSearch query: {query}")
    print("\nSearching AstraDB...")

    try:
        results = search_knowledge_base(
            query=query,
            top_k=3,
            similarity_threshold=0.5
        )
        print(f"\nResults:\n{results}")
    except Exception as e:
        print(f"\nError: {e}")

    print("\n" + "=" * 60 + "\n")

def demo_list_sheets():
    """Demo listing sheets in an Excel file"""
    print("=" * 60)
    print("Demo: List Excel Sheets")
    print("=" * 60)

    # You can replace this with your actual file path
    test_file = "sample_rfp.xlsx"

    print(f"\nFile: {test_file}")
    print("\nNote: This will fail if the file doesn't exist")
    print("Replace 'sample_rfp.xlsx' with an actual file path to test")

    try:
        result = list_excel_sheets(test_file)
        print(f"\nSheets:\n{result}")
    except Exception as e:
        print(f"\nExpected error (file not found): {e}")

    print("\n" + "=" * 60 + "\n")

if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  MCP Server Tools Demo".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n")

    print("This script demonstrates calling MCP tools directly")
    print("from Python without using HTTP requests.\n")

    # Run demos
    try:
        demo_search_knowledge_base()
        demo_answer_question()
        demo_list_sheets()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print("\nYour MCP server is running on port 8001")
    print("It's ready for WatsonX Orchestrate integration.")
    print()
