import time
import re
import os
import sqlite3
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
    "OUT_OF_SCOPE": "I can help with VTU-related subjects, syllabus, study material, previous-year questions, and exam preparation. 📚",

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


def get_pyq_context_from_db(question: str, subject_code: str = "") -> str:
    """Retrieves structured PYQ question groups and question items from sqlite vtuva.db."""
    code_match = re.search(r"\b([A-Z]{2,5}\d{2,4}[A-Z]?)\b", question.upper())
    subj = code_match.group(1) if code_match else (subject_code.upper().strip() if subject_code and subject_code.strip() not in ("GENERAL", "ALL") else "")

    if not subj:
        return ""

    try:
        db_path = Path(__file__).resolve().parent.parent.parent / "vtuva.db"
        if not db_path.exists():
            db_path = Path("vtuva.db")
        if not db_path.exists():
            return ""

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Query pyq_questions
        cursor.execute(
            "SELECT main_question, sub_question, question_text, marks, year, session "
            "FROM pyq_questions WHERE UPPER(subject_code) LIKE ? ORDER BY id",
            (f"%{subj}%",)
        )
        questions = cursor.fetchall()

        # Query pyq_question_groups
        cursor.execute(
            "SELECT canonical_question, repetition_count, years_asked, importance_tier "
            "FROM pyq_question_groups WHERE UPPER(subject_code) LIKE ? ORDER BY repetition_count DESC",
            (f"%{subj}%",)
        )
        groups = cursor.fetchall()
        conn.close()

        if not questions and not groups:
            return ""

        def parse_module(main_q_str):
            if not main_q_str: return 1
            num_match = re.search(r"\d+", str(main_q_str))
            if not num_match: return 1
            n = int(num_match.group(0))
            if n in (1, 2): return 1
            elif n in (3, 4): return 2
            elif n in (5, 6): return 3
            elif n in (7, 8): return 4
            elif n in (9, 10): return 5
            return 1

        lines = [f"=== STRUCTURED PREVIOUS YEAR QUESTIONS (PYQs) FOR SUBJECT: {subj} ==="]

        if groups:
            lines.append("\n### Most Repeated / High-Frequency Questions:")
            for g in groups:
                canon_q, rep_cnt, years, tier = g
                lines.append(f"- **[Repeated {rep_cnt}x | Years: {years}]** {canon_q} ({tier})")

        if questions:
            lines.append("\n### PYQ Items by VTU Exam Module:")
            by_mod = {1: [], 2: [], 3: [], 4: [], 5: []}
            seen_texts = set()
            for q in questions:
                mq, sq, text, marks, year, sess = q
                m_num = parse_module(mq)
                clean_t = text.strip()
                if clean_t not in seen_texts:
                    seen_texts.add(clean_t)
                    by_mod[m_num].append(f"- **[{mq}{sq if sq else ''}]** {clean_t} ({marks} Marks)")

            for m_i in range(1, 6):
                if by_mod[m_i]:
                    lines.append(f"\n#### Module {m_i}:")
                    for q_item in by_mod[m_i]:
                        lines.append(q_item)

        return "\n".join(lines)
    except Exception as e:
        print(f"[DB PYQ Lookup Error]: {e}")
        return ""


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


def ask_question(question: str, history=None, subject: str = "General", filter_dict: dict = None) -> Dict[str, Any]:
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
    db_pyq_context = get_pyq_context_from_db(standalone_question, subject_code=subject)

    t_vector_start = time.perf_counter()
    retriever = get_retriever(k=4, filter_dict=filter_dict)
    docs = retriever.invoke(search_query)
    t_vector = time.perf_counter() - t_vector_start

    sources = extract_sources(docs)

    # Deduplicate context chunks
    unique_contents = []
    seen_hashes = set()
    for doc in docs:
        c_str = doc.page_content.strip()
        c_hash = hash(c_str[:200])
        if c_hash not in seen_hashes:
            seen_hashes.add(c_hash)
            unique_contents.append(c_str)

    vector_context = "\n\n".join(unique_contents)

    context_parts = []
    if db_pyq_context:
        context_parts.append(db_pyq_context)
    if vector_context:
        context_parts.append(vector_context)

    context = "\n\n".join(context_parts)

    if not context or not context.strip():
        t_total = time.perf_counter() - t_start
        print(f"\n[PERF TIMING] Rewrite: {t_rewrite:.3f}s | Vector Search: {t_vector:.3f}s | TOTAL: {t_total:.3f}s")
        return {"answer": "I couldn't find enough information in the available VTU knowledge base to answer this accurately.", "sources": []}

    t_llm_start = time.perf_counter()
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


def prepare_rag_context(question: str, history=None, filter_dict: dict = None) -> Tuple[str, List[Dict[str, Any]], str, float, float]:
    """Helper to prepare standalone question, sources, and context for streaming."""
    q_clean = question.strip() if question else ""

    intent = detect_intent(q_clean)

    if intent in CASUAL_RESPONSES:
        return q_clean, [], f"__{intent}__", 0.0, 0.0

    t_rewrite_start = time.perf_counter()
    standalone_question = rewrite_question_with_history(q_clean, history) if history else q_clean
    t_rewrite = time.perf_counter() - t_rewrite_start

    search_query = enhance_pyq_search_query(standalone_question)
    db_pyq_context = get_pyq_context_from_db(
        standalone_question,
        subject_code=filter_dict.get("subject_code") if filter_dict else ""
    )

    t_vector_start = time.perf_counter()
    retriever = get_retriever(k=4, filter_dict=filter_dict)
    docs = retriever.invoke(search_query)
    t_vector = time.perf_counter() - t_vector_start

    sources = extract_sources(docs)

    # Deduplicate context chunks
    unique_contents = []
    seen_hashes = set()
    for doc in docs:
        c_str = doc.page_content.strip()
        c_hash = hash(c_str[:200])
        if c_hash not in seen_hashes:
            seen_hashes.add(c_hash)
            unique_contents.append(c_str)

    vector_context = "\n\n".join(unique_contents)

    context_parts = []
    if db_pyq_context:
        context_parts.append(db_pyq_context)
    if vector_context:
        context_parts.append(vector_context)

    context = "\n\n".join(context_parts)

    return standalone_question, sources, context, t_rewrite, t_vector