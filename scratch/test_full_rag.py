import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "backend"))

from backend.rag.pipeline import ask_question

def test_full_rag_pipeline():
    print("==================================================")
    print(" TESTING FULL CONTEXTUAL RAG PIPELINE")
    print("==================================================\n")

    history = [
        {"question": "What is BFS?", "answer": "BFS stands for Breadth First Search. It is a graph search technique."}
    ]

    res = ask_question("What are its advantages?", history=history)
    print("ANSWER GENERATED:")
    print(res.get("answer")[:300] + "...")
    print("\nSOURCES RETRIEVED:", len(res.get("sources", [])))

if __name__ == "__main__":
    test_full_rag_pipeline()
