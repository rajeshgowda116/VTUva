import os
import re
from typing import List, Dict, Optional
from dotenv import load_dotenv

try:
    from .generate import get_llm, extract_text_from_chunk
except ImportError:
    from generate import get_llm, extract_text_from_chunk

load_dotenv()

GREETINGS = {
    "hi", "hii", "hiii", "hello", "hey", "heyy", "hola", "namaste",
    "good morning", "good afternoon", "good evening", "howdy",
    "who are you", "what is vtuva", "thanks", "thank you", "bye", "goodbye",
    "good", "nice", "great", "okay", "ok", "got it", "understood"
}

FOLLOWUP_PRONOUNS = {
    "it", "its", "this", "that", "these", "those", "they", "them", "their",
    "his", "her", "such", "same", "one", "second", "third", "former", "latter", "above"
}

FOLLOWUP_PHRASES = [
    "give an example", "give me an example", "give example", "example of this", "explain more",
    "tell me more", "why so", "how so", "what about", "how about", "types of it", "previous one",
    "same topic", "above", "its advantages", "its disadvantages", "its types",
    "its features", "its applications", "how to use it", "why do we use it",
    "more details", "how does it work", "first topic", "second topic", "next topic",
    "previous topic", "the second one", "the first one", "the third one",
    "module 1", "module 2", "module 3", "module 4", "module 5",
    "unit 1", "unit 2", "unit 3", "unit 4", "unit 5",
    "chapter 1", "chapter 2", "explain it simply", "in simple terms",
    "advantages", "disadvantages", "features", "applications", "benefits", "limitations"
]


def is_greeting(question: str) -> bool:
    """Checks if a user input is a casual greeting or conversational message."""
    if not question:
        return False
    q_clean = question.lower().strip().strip("!.,?")
    return q_clean in GREETINGS


def is_follow_up_question(question: str, history: Optional[List[Dict[str, str]]] = None) -> bool:
    """
    Check if a question requires conversation history context.
    Returns True if the question contains pronouns, follow-up phrases, or lacks explicit subjects when history exists.
    """
    if not question or not question.strip():
        return False

    if is_greeting(question):
        return False

    if not history or len(history) == 0:
        return False

    q_lower = question.lower().strip()

    # Check for explicit follow-up phrases
    for phrase in FOLLOWUP_PHRASES:
        if phrase in q_lower:
            return True

    # Check for course code in current question e.g. BCS502, 21CS51, etc.
    has_course_code = bool(re.search(r"([a-z]{2,5}\d{2,4}|21[a-z]{2,3}\d{2}|18[a-z]{2,3}\d{2})", q_lower))

    # Match exact word tokens
    words = set(re.findall(r'\b\w+\b', q_lower))

    # Check for referential pronouns or relative terms
    if words.intersection(FOLLOWUP_PRONOUNS):
        return True

    # If question lacks course code and is relatively short (< 8 words), or starts with relative conjunctions/verbs
    if not has_course_code:
        if len(words) <= 7:
            return True
        if re.match(r"^(what|how|why|explain|describe|give|list|show|and|or|also)\b", q_lower):
            # Check if history contains a specific subject context (like BCS502, BFS, DBMS, etc.)
            last_q = history[-1].get("question", "").lower()
            if any(kw in last_q or kw in history[-1].get("answer", "").lower() for kw in ["bcs", "module", "bfs", "dfs", "dbms", "os", "algorithm", "normalization"]):
                return True

    return False


def rewrite_question_with_history(current_question: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Rewrites the user question into a standalone question using conversation history.
    If history is empty or question is standalone / greeting, returns current_question unchanged immediately.
    """
    if not current_question or not current_question.strip():
        return current_question

    current_question_clean = current_question.strip()

    if not history or len(history) == 0:
        return current_question_clean

    if not is_follow_up_question(current_question_clean, history):
        return current_question_clean

    # Use standard LLM instance for question contextualization
    llm = get_llm()
    if not llm:
        return current_question_clean

    # Format last 4 exchanges for comprehensive multi-turn subject tracking
    recent_history = history[-4:]
    formatted_turns = []
    for h in recent_history:
        q = h.get("question", "").strip()
        a = h.get("answer", "").strip()
        a_short = a[:250] + "..." if len(a) > 250 else a
        if q:
            formatted_turns.append(f"User: {q}\nAssistant: {a_short}")

    if not formatted_turns:
        return current_question_clean

    conversation_history = "\n\n".join(formatted_turns)

    prompt = f"""Given the following conversation history and a follow-up question from a student, rewrite the follow-up question into a single, complete, standalone search query that contains all necessary subject context (such as VTU course code e.g. BCS502, module number, topic names, or terms referenced by pronouns like 'its', 'this', 'module 1', 'the second one', 'give an example', 'what about DFS', etc.).

RULES:
1. Do NOT answer the question.
2. Return ONLY the rewritten standalone question text.
3. If the question is already fully explicit and standalone, return it as is.
4. Keep the rewritten query concise and natural.

Conversation History:
{conversation_history}

Follow-up Question:
{current_question_clean}

Standalone Question:"""

    try:
        response = llm.invoke(prompt)
        content = extract_text_from_chunk(response) if response else current_question_clean
        rewritten = content.strip().strip('"\'`') if content else current_question_clean
        if "\n" in rewritten:
            rewritten = rewritten.split("\n")[0].strip()
        return rewritten if rewritten else current_question_clean
    except Exception as e:
        print(f"[Contextualizer Error] Failed to rewrite question: {e}")
        # Rule-based fallback for API rate limits or network issues:
        last_exchange = history[-1]
        last_q = last_exchange.get("question", "")
        course_match = re.search(r"([A-Z]{2,5}\d{2,4}|BCS\d{3}|21[A-Z]{2,3}\d{2})", last_q, re.IGNORECASE)
        topic_match = re.search(r"\b(BFS|DFS|DBMS|OS|Virtual Memory|Transformer|Normalization)\b", last_q, re.IGNORECASE)
        context_term = course_match.group(0) if course_match else (topic_match.group(0) if topic_match else "")
        if not context_term:
            words = [w for w in re.findall(r"\b[A-Za-z0-9_]+\b", last_q) if w.lower() not in ["what", "is", "explain", "the", "are", "about", "give", "me", "a", "an"]]
            if words:
                context_term = " ".join(words[:3])

        if context_term:
            return f"{current_question_clean} ({context_term})"
        return current_question_clean


