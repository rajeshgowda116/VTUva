import sys, os
sys.path.insert(0, os.path.abspath('.'))

from backend.rag.retriever import get_vector_store

vs = get_vector_store()
coll = vs._collection
print(f"Total documents in Chroma collection: {coll.count()}")

# Get sample metadata
data = coll.get(limit=20)
print("\nSample metadatas in Chroma:")
for m in data.get('metadatas', [])[:10]:
    print("  ", m)

# Search Chroma for BCS502
res = vs.similarity_search("BCS502 Data Communication Computer Networks", k=5)
print(f"\nSimilarity search for BCS502 returned {len(res)} docs:")
for r in res:
    print(f"Source: {r.metadata}")
    print(r.page_content[:200])
    print("-" * 40)
