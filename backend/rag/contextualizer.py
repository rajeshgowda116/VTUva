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
    "who are you", "what is vtuva", "thanks", "thank you", "bye", "goodbye"
}

FOLLOWUP_PRONOUNS = {
    "it", "its", "this", "that", "these", "those", "they", "them", "their", "his", "her"
}

FOLLOWUP_PHRASES = [
    "give an example", "give me an example", "example of this", "explain more",
    "tell me more", "why so", "how so", "what about", "types of it", "previous one",
    "same topic", "above", "its advantages", "its disadvantages", "its types",
    "its features", "its applications", "how to use it", "why do we use it",
    "give example", "more details", "how does it work"
]


def is_greeting(question: str) -> bool:
    """Checks if a user input is a casual greeting or conversational message."""
    if not question:
        return False
    q_clean = question.lower().strip().strip("!.,?")
    return q_clean in GREETINGS


def is_follow_up_question(question: str) -> bool:
    """
    Fast, lightweight heuristic to check if a question is a follow-up.
    Returns True if the question contains referential pronouns or phrases.
    Returns False if the question is standalone or a greeting.
    """
    if not question or not question.strip():
        return False

    if is_greeting(question):
        return False

    q_lower = question.lower().strip()

    # Check for explicit follow-up phrases
    for phrase in FOLLOWUP_PHRASES:
        if phrase in q_lower:
            return True

    # Match exact word tokens
    words = set(re.findall(r'\b\w+\b', q_lower))

    # Check for referential pronouns
    if words.intersection(FOLLOWUP_PRONOUNS):
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

    if not history:
        return current_question_clean

    # FAST PATH: Skip LLM call if question is standalone or greeting!
    if not is_follow_up_question(current_question_clean):
        return current_question_clean

    # Use ultra-fast flash-lite model for quick question contextualization
    llm = get_llm(model_override="gemini-2.5-flash-lite")
    if not llm:
        return current_question_clean

    # Format last 1 exchange for minimum token count and maximum speed
    recent_item = history[-1]
    q = recent_item.get("question", "").strip()
    a = recent_item.get("answer", "").strip()[:100]
    conversation_history = f"User: {q}\nAssistant: {a}"

    prompt = f"""Rewrite latest user question into a standalone question using context.
History:
{conversation_history}
Question: {current_question_clean}
Standalone Question:"""

    try:
        response = llm.invoke(prompt)
        content = extract_text_from_chunk(response) if response else current_question_clean
        rewritten = content.strip().strip('"\'`') if content else current_question_clean
        return rewritten if rewritten else current_question_clean
    except Exception as e:
        print(f"[Contextualizer Error] Failed to rewrite question: {e}")
        return current_question_clean
