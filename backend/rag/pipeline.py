import time
import re
from pathlib import Path
from typing import Generator, Tuple, List, Dict, Any

try:
    from backend.app.chat.intent import detect_intent
except ImportError:
    try:
        from app.chat.intent import detect_intent
    except ImportError:
        def detect_intent(msg: str) -> str:
            return "UNKNOWN"

try:
    from .retriever import get_retriever
    from .generate import generate_answer, generate_answer_stream
    from .contextualizer import rewrite_question_with_history
except ImportError:
    from retriever import get_retriever
    from generate import generate_answer, generate_answer_stream
    from contextualizer import rewrite_question_with_history


CASUAL_RESPONSES = {

    # Greetings
    "GREETING": "Hey! 👋 What are you studying today?",
    "GREETING_MORNING": "Good morning! ☀️ Ready to study?",
    "GREETING_AFTERNOON": "Good afternoon! 👋 What VTU topic are we working on?",
    "GREETING_EVENING": "Good evening! 🌙 What would you like to study?",
    "GREETING_NIGHT": "Good night! 🌙 Don't forget to get some rest after studying!",

    # Thanks
    "CASUAL_THANKS": "You're welcome! 😊 Good luck with your studies!",
    "CASUAL_THANKS_2": "Anytime! 📚 I'm here whenever you need help.",
    "CASUAL_THANKS_3": "You're welcome! Keep learning! 🚀",

    # Positive feedback
    "CASUAL_GOOD": "Glad that helped! 😊",
    "CASUAL_GREAT": "Awesome! 🚀 Keep going!",
    "CASUAL_NICE": "Glad you liked it! 😊",
    "CASUAL_PERFECT": "Great! 👍 Let's keep going.",

    # OK / acknowledgement
    "CASUAL_OK": "Sure! 👍 Ask me whenever you're ready.",
    "CASUAL_GOT_IT": "Perfect! 👍",
    "CASUAL_UNDERSTOOD": "Great! 😊 Let's move to the next topic.",
    "CASUAL_SURE": "Sure! What would you like to know?",

    # Goodbye
    "CASUAL_BYE": "Bye! 👋 Good luck with your studies!",
    "CASUAL_GOODBYE": "See you! 📚 Keep learning and all the best!",
    "CASUAL_SEE_YOU": "See you later! 👋",

    # General casual
    "CASUAL": "Glad to help! 😊 Ask me anything about your VTU subjects.",
    "CASUAL_HELP": "Of course! 📚 What VTU topic do you need help with?",
    "CASUAL_READY": "I'm ready! 🚀 Send me your question.",
    "CASUAL_START": "Let's get started! 📖 What's your question?",
    "CASUAL_CONTINUE": "Absolutely! 👍 What's next?",
    "CASUAL_MORE": "Sure! Tell me what you'd like to explore next.",

    # Encouragement
    "CASUAL_MOTIVATION": "You've got this! 💪 Keep going.",
    "CASUAL_STUDY": "Let's make some progress today! 📚",
    "CASUAL_EXAM": "Stay focused and keep practicing! 💪📖",
    "CASUAL_CONFIDENT": "Nice! Keep building your understanding step by step. 🚀",

    # Identity
    "WHO_ARE_YOU": "I'm VTUva, your AI study assistant for VTU subjects. 🤖📚",
    "WHAT_IS_VTUVA": "I'm VTUva — an AI study assistant designed to help with VTU subjects, concepts, and exam preparation. 📚",

    # When user asks for help
    "NEED_HELP": "Of course! 😊 Send me the topic or question you're working on.",
    "CAN_YOU_HELP": "Absolutely! 📚 Ask your VTU question and I'll help you understand it.",

    # Out of Scope / Non-VTU
    "OUT_OF_SCOPE": "I'm focused on VTU academic topics. Ask me about your syllabus, subjects, notes, previous-year questions, or exam preparation. 📚",

    # Default
    "DEFAULT": "I'm here to help! 😊 Ask me a question about your VTU studies."
}


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
                "file_path": f"/data/prev_qustions/{clean_name}"
            })
    return sources


def enhance_pyq_search_query(question: str) -> str:
    q_clean = question.strip()

    # Typo normalization
    typos = {
        r"\bsenser\b": "sensor",
        r"\bsensers\b": "sensors",
        r"\bprocesser\b": "processor",
        r"\bprocessers\b": "processors",
    }
    for pattern, replacement in typos.items():
        q_clean = re.sub(pattern, replacement, q_clean, flags=re.IGNORECASE)

    is_pyq_intent = re.search(r"(repeat|repet|frequent|freq|most\s+asked|pyq|pyqs|previous\s+year)", q_clean, re.IGNORECASE)
    has_course_code = re.search(r"([A-Z]{2,5}\d{2,4}|21[A-Z]{2,3}\d{2}|18[A-Z]{2,3}\d{2})", q_clean, re.IGNORECASE)

    if is_pyq_intent and not has_course_code:
        return f"{q_clean} PYQ Most Asked Questions Summary repeated questions BCS501 Software Engineering"
    return q_clean


def ask_question(question: str, history=None, subject: str = "General") -> Dict[str, Any]:
    t_start = time.perf_counter()

    if not question or not question.strip():
        return {"answer": "Please enter a valid question.", "sources": []}

    q_clean = question.strip()

    # Step 1 Intent Router Check
    intent = detect_intent(q_clean)

    if intent in CASUAL_RESPONSES:
        return {
            "answer": CASUAL_RESPONSES[intent],
            "sources": []
        }

    # Only UNKNOWN continues to RAG search
    t_rewrite_start = time.perf_counter()
    standalone_question = rewrite_question_with_history(q_clean, history) if history else q_clean
    t_rewrite = time.perf_counter() - t_rewrite_start

    search_query = enhance_pyq_search_query(standalone_question)

    t_vector_start = time.perf_counter()
    retriever = get_retriever(k=4)
    docs = retriever.invoke(search_query)
    t_vector = time.perf_counter() - t_vector_start

    sources = extract_sources(docs)

    if not docs:
        t_total = time.perf_counter() - t_start
        print(f"\n[PERF TIMING] Rewrite: {t_rewrite:.3f}s | Vector Search: {t_vector:.3f}s | TOTAL: {t_total:.3f}s")
        return {"answer": "I couldn't find enough information about that in my current VTU knowledge base.", "sources": []}

    t_llm_start = time.perf_counter()
    context = "\n\n".join(doc.page_content for doc in docs)
    answer = generate_answer(standalone_question, context, subject=subject)
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

    intent = detect_intent(q_clean)

    if intent in CASUAL_RESPONSES:
        return q_clean, [], f"__{intent}__", 0.0, 0.0

    t_rewrite_start = time.perf_counter()
    standalone_question = rewrite_question_with_history(q_clean, history) if history else q_clean
    t_rewrite = time.perf_counter() - t_rewrite_start

    search_query = enhance_pyq_search_query(standalone_question)

    t_vector_start = time.perf_counter()
    retriever = get_retriever(k=4)
    docs = retriever.invoke(search_query)
    t_vector = time.perf_counter() - t_vector_start

    sources = extract_sources(docs)
    context = "\n\n".join(doc.page_content for doc in docs)

    return standalone_question, sources, context, t_rewrite, t_vector