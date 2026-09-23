import time
from pathlib import Path
from typing import Generator, Tuple, List, Dict, Any

try:
    from .retriever import get_retriever
    from .generate import generate_answer, generate_answer_stream
    from .contextualizer import rewrite_question_with_history, is_greeting
except ImportError:
    from retriever import get_retriever
    from generate import generate_answer, generate_answer_stream
    from contextualizer import rewrite_question_with_history, is_greeting


GREETING_RESPONSE = "Hello! I am VTUva, your VTU engineering study assistant. How can I help you with your VTU subjects, notes, or syllabus today?"


def extract_sources(docs: List[Any]) -> List[Dict[str, Any]]:
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
    return sources


def ask_question(question: str, history=None) -> Dict[str, Any]:
    t_start = time.perf_counter()

    if not question or not question.strip():
        return {"answer": "Please enter a valid question.", "sources": []}

    q_clean = question.strip()

    # Fast Path for Greetings
    if is_greeting(q_clean):
        return {
            "answer": GREETING_RESPONSE,
            "sources": []
        }

    # 1. Context Rewriting
    t_rewrite_start = time.perf_counter()
    standalone_question = rewrite_question_with_history(q_clean, history) if history else q_clean
    t_rewrite = time.perf_counter() - t_rewrite_start

    # 2. Vector Retrieval (k=4)
    t_vector_start = time.perf_counter()
    retriever = get_retriever(k=4)
    docs = retriever.invoke(standalone_question)
    t_vector = time.perf_counter() - t_vector_start

    sources = extract_sources(docs)

    if not docs:
        t_total = time.perf_counter() - t_start
        print(f"\n[PERF TIMING] Rewrite: {t_rewrite:.3f}s | Vector Search: {t_vector:.3f}s | TOTAL: {t_total:.3f}s")
        return {"answer": "No relevant information found in the VTU documents.", "sources": []}

    # 3. LLM Generation
    t_llm_start = time.perf_counter()
    context = "\n\n".join(doc.page_content for doc in docs)
    answer = generate_answer(standalone_question, context)
    t_llm = time.perf_counter() - t_llm_start

    t_total = time.perf_counter() - t_start

    print(f"\n[PERF TIMING]\n"
          f"  - Context Rewriting : {t_rewrite:.3f}s\n"
          f"  - Vector Search (k=4): {t_vector:.3f}s\n"
          f"  - LLM Generation   : {t_llm:.3f}s\n"
          f"  - TOTAL TIME       : {t_total:.3f}s\n")

    return {
        "answer": answer,
        "sources": sources
    }


def prepare_rag_context(question: str, history=None) -> Tuple[str, List[Dict[str, Any]], str, float, float]:
    """Helper to prepare standalone question, sources, and context for streaming."""
    q_clean = question.strip() if question else ""

    if is_greeting(q_clean):
        return q_clean, [], "__GREETING__", 0.0, 0.0

    t_rewrite_start = time.perf_counter()
    standalone_question = rewrite_question_with_history(q_clean, history) if history else q_clean
    t_rewrite = time.perf_counter() - t_rewrite_start

    t_vector_start = time.perf_counter()
    retriever = get_retriever(k=4)
    docs = retriever.invoke(standalone_question)
    t_vector = time.perf_counter() - t_vector_start

    sources = extract_sources(docs)
    context = "\n\n".join(doc.page_content for doc in docs)

    return standalone_question, sources, context, t_rewrite, t_vector