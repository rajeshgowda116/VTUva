import sys
from pathlib import Path

# Add project root and backend to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "backend"))

from backend.rag.contextualizer import rewrite_question_with_history

def run_tests():
    print("==================================================")
    print(" RUNNING CONTEXTUAL QUESTION REWRITER VERIFICATION")
    print("==================================================\n")

    # TEST 1: BFS
    history1 = [
        {"question": "What is BFS?", "answer": "BFS stands for Breadth First Search. It is a graph traversal algorithm."}
    ]
    q1 = "What are its advantages?"
    rewritten1 = rewrite_question_with_history(q1, history1)
    print(f"TEST 1 [BFS]\n  Input: {q1}\n  Rewritten: {rewritten1}\n")

    # TEST 2: Normalization
    history2 = [
        {"question": "Explain normalization.", "answer": "Normalization is the process of organizing data in a database to reduce redundancy."}
    ]
    q2 = "Give me an example."
    rewritten2 = rewrite_question_with_history(q2, history2)
    print(f"TEST 2 [Normalization]\n  Input: {q2}\n  Rewritten: {rewritten2}\n")

    # TEST 3: Deadlock
    history3 = [
        {"question": "What is deadlock?", "answer": "Deadlock is a set of blocked processes each holding a resource and waiting for another resource."}
    ]
    q3 = "How can it be prevented?"
    rewritten3 = rewrite_question_with_history(q3, history3)
    print(f"TEST 3 [Deadlock]\n  Input: {q3}\n  Rewritten: {rewritten3}\n")

    # TEST 4: Machine Learning
    history4 = [
        {"question": "Explain machine learning.", "answer": "Machine learning is a field of artificial intelligence focused on building systems that learn from data."}
    ]
    q4 = "What are its types?"
    rewritten4 = rewrite_question_with_history(q4, history4)
    print(f"TEST 4 [Machine Learning]\n  Input: {q4}\n  Rewritten: {rewritten4}\n")

    # TEST 5: Standalone question switch
    history5 = [
        {"question": "What is DBMS?", "answer": "Database Management System (DBMS) is software used to store and retrieve data."}
    ]
    q5 = "What is normalization?"
    rewritten5 = rewrite_question_with_history(q5, history5)
    print(f"TEST 5 [Standalone Switch]\n  Input: {q5}\n  Rewritten: {rewritten5}\n")

if __name__ == "__main__":
    run_tests()
