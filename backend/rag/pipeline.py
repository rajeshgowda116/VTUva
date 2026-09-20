from pathlib import Path

try:
    from .retriever import get_retriever
    from .generate import generate_answer
except ImportError:
    from retriever import get_retriever
    from generate import generate_answer


def ask_question(question: str):
    if not question or not question.strip():
        return {"answer": "Please enter a valid question.", "sources": []}

    retriever = get_retriever()
    docs = retriever.invoke(question)

    print(f"\n[INFO] Retrieved {len(docs)} document chunks")

    sources = []
    seen = set()
    for doc in docs:
        file_name = doc.metadata.get("file_name") or doc.metadata.get("source", "VTU Document")
        page = doc.metadata.get("page", 1)
        clean_name = Path(file_name).name if file_name else "VTU Document"
        key = (clean_name, page)
        if key not in seen:
            seen.add(key)
            snippet = doc.page_content[:400].strip() + ("..." if len(doc.page_content) > 400 else "")
            sources.append({
                "file_name": clean_name,
                "page": page,
                "snippet": snippet,
                "file_path": f"/data/frist_sem/{clean_name}"
            })

    if not docs:
        return {"answer": "No relevant information found in the VTU documents.", "sources": []}

    context = "\n\n".join(doc.page_content for doc in docs)
    answer = generate_answer(question, context)

    return {
        "answer": answer,
        "sources": sources
    }


if __name__ == "__main__":
    while True:
        question = input("\nAsk a question: ")
        if question.lower() in ["exit", "quit"]:
            break
        res = ask_question(question)
        print("\nVTUva:")
        print(res.get("answer"))
        print("\nSources:", res.get("sources"))