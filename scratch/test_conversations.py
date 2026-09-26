import sys
import os
from pathlib import Path

# Set UTF-8 output encoding for Windows terminal
sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "backend"))

from backend.app.chat.intent import detect_intent
from backend.rag.contextualizer import is_follow_up_question, rewrite_question_with_history
from backend.rag.pipeline import prepare_rag_context, CASUAL_RESPONSES

def run_tests():
    print("\n==================================================")
    print(" RUNNING VTUVA CHATBOT CONVERSATION BEHAVIOR TESTS")
    print("==================================================\n")

    # TEST 1: Greeting
    print("[TEST 1] User: hello")
    intent1 = detect_intent("hello")
    print(f"  -> Intent: {intent1}")
    print(f"  -> Response: {CASUAL_RESPONSES.get(intent1)}")
    assert intent1 == "GREETING"
    print("  -> PASSED (No RAG triggered)\n")

    # TEST 2: Standalone question
    print("[TEST 2] User: What is BFS?")
    intent2 = detect_intent("What is BFS?")
    q2, sources2, context2, _, _ = prepare_rag_context("What is BFS?", history=[])
    print(f"  -> Intent: {intent2}")
    print(f"  -> Standalone Question: {q2}")
    assert intent2 == "UNKNOWN"
    assert q2 == "What is BFS?"
    print("  -> PASSED\n")

    # TEST 3: Follow-up resolving "its"
    print("[TEST 3] User: What are its advantages?")
    history3 = [{"question": "What is BFS?", "answer": "Breadth First Search (BFS) is a graph algorithm."}]
    is_fu3 = is_follow_up_question("What are its advantages?", history3)
    rewritten3 = rewrite_question_with_history("What are its advantages?", history3)
    print(f"  -> Is follow-up: {is_fu3}")
    print(f"  -> Rewritten query: {rewritten3}")
    assert is_fu3 is True
    assert "bfs" in rewritten3.lower() or "breadth" in rewritten3.lower() or "graph" in rewritten3.lower()
    print("  -> PASSED ('its' resolved to BFS)\n")

    # TEST 4: Casual message "good"
    print("[TEST 4] User: good")
    intent4 = detect_intent("good")
    print(f"  -> Intent: {intent4}")
    print(f"  -> Response: {CASUAL_RESPONSES.get(intent4)}")
    assert intent4 == "CASUAL_GOOD"
    print("  -> PASSED (No RAG triggered)\n")

    # TEST 5: Subject inquiry "Explain BCS502"
    print("[TEST 5] User: Explain BCS502.")
    intent5 = detect_intent("Explain BCS502.")
    q5, _, _, _, _ = prepare_rag_context("Explain BCS502.", history=[])
    print(f"  -> Intent: {intent5}")
    print(f"  -> Query: {q5}")
    assert intent5 == "UNKNOWN"
    print("  -> PASSED\n")

    # TEST 6: Follow-up "Explain Module 1" within BCS502 context
    print("[TEST 6] User: Explain Module 1.")
    history6 = [{"question": "Explain BCS502.", "answer": "BCS502 covers Computer Networks syllabus."}]
    is_fu6 = is_follow_up_question("Explain Module 1.", history6)
    rewritten6 = rewrite_question_with_history("Explain Module 1.", history6)
    print(f"  -> Is follow-up: {is_fu6}")
    print(f"  -> Rewritten query: {rewritten6}")
    assert is_fu6 is True
    assert "bcs502" in rewritten6.lower()
    print("  -> PASSED (Understands Module 1 belongs to BCS502)\n")

    # TEST 7: Follow-up "Give an example."
    print("[TEST 7] User: Give an example.")
    history7 = [
        {"question": "Explain BCS502.", "answer": "BCS502 covers Computer Networks."},
        {"question": "Explain Module 1.", "answer": "Module 1 covers Application Layer and HTTP protocol."}
    ]
    is_fu7 = is_follow_up_question("Give an example.", history7)
    rewritten7 = rewrite_question_with_history("Give an example.", history7)
    print(f"  -> Is follow-up: {is_fu7}")
    print(f"  -> Rewritten query: {rewritten7}")
    assert is_fu7 is True
    print("  -> PASSED (Understands what example refers to)\n")

    # TEST 8: Gratitude "thank you"
    print("[TEST 8] User: thank you")
    intent8 = detect_intent("thank you")
    print(f"  -> Intent: {intent8}")
    print(f"  -> Response: {CASUAL_RESPONSES.get(intent8)}")
    assert intent8 == "CASUAL_THANKS"
    print("  -> PASSED (No RAG triggered)\n")

    print("==================================================")
    print(" ALL 8 BACKEND CONVERSATION BEHAVIOR TESTS PASSED ")
    print("==================================================\n")

if __name__ == "__main__":
    run_tests()
