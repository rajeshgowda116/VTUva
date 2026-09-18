from typing import Dict, Any, List

try:
    from backend.rag.retriever import get_retriever
    from backend.rag.chain import get_chain
except ImportError:
    from retriever import get_retriever
    from chain import get_chain


def ask_vtuva(question: str) -> Dict[str, Any]:
    """Execute RAG pipeline: Retrieve context from Qdrant and generate answer with Gemini LLM."""
    if not question or not question.strip():
        return {
            "answer": "Please provide a valid question.",
            "sources": []
        }

    # 1. Retrieve relevant chunks
    retriever = get_retriever()
    retrieved_docs = retriever.invoke(question)

    if not retrieved_docs:
        return {
            "answer": "I couldn't find this information in the provided VTU documents.",
            "sources": []
        }

    # 2. Format context text & extract sources
    context_blocks: List[str] = []
    sources: List[Dict[str, Any]] = []

    for idx, doc in enumerate(retrieved_docs, start=1):
        context_blocks.append(f"--- Document Chunk {idx} ---\n{doc.page_content}")
        file_name = doc.metadata.get("file_name") or doc.metadata.get("source", "Unknown")
        page = doc.metadata.get("page", "N/A")

        source_info = {"file_name": file_name, "page": page}
        if source_info not in sources:
            sources.append(source_info)

    formatted_context = "\n\n".join(context_blocks)

    # 3. Run Gemini Chain
    chain = get_chain()
    answer = chain.invoke({
        "context": formatted_context,
        "question": question
    })

    return {
        "answer": answer,
        "sources": sources
    }


if __name__ == "__main__":
    sample_question = "what is Electrochemical Sensors?"
    print(f"❓ Testing Question: {sample_question}")
    result = ask_vtuva(sample_question)
    print(f"🤖 Answer:\n{result['answer']}")
    print(f"📚 Sources:\n{result['sources']}")
