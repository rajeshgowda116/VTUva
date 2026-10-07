import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))

from backend.rag.pipeline import ask_question

print("=== TESTING PYQ QUERY FOR BCS502 ===")
q = "Can you show top repeated PYQs for BCS502?"
res = ask_question(q, subject="BCS502")

print("\n--- ANSWER FROM RAG PIPELINE ---")
print(res["answer"])
print("\n--- SOURCES ---")
print(res["sources"])
