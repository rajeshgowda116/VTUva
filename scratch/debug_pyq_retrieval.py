import sys, os
sys.path.insert(0, os.path.abspath('.'))

from backend.rag.pipeline import ask_question, enhance_pyq_search_query
from backend.rag.retriever import get_retriever

q = "Can you show top repeated PYQs for BCS502?"
print("Original Question:", q)

search_q = enhance_pyq_search_query(q)
print("Enhanced Search Query:", search_q)

retriever = get_retriever(k=4)
docs = retriever.invoke(search_q)
print(f"Retrieved {len(docs)} documents:")
for i, d in enumerate(docs):
    print(f"--- Doc {i+1} ({d.metadata.get('file_name')}) ---")
    print(d.page_content[:300])

res = ask_question(q, subject="BCS502")
print("\n=== ASK QUESTION RESULT ===")
print("Answer:", res.get("answer"))
print("Sources:", res.get("sources"))
