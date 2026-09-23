import os
import re
from typing import List, Dict, Optional
from dotenv import load_dotenv

try:
    from .generate import get_llm, extract_text_from_chunk
except ImportError:
    from generate import get_llm, extract_text_from_chunk

load_dotenv()

FOLLOWUP_PRONOUNS = {
    "it", "its", "this", "that", "these", "those", "they", "them", "their", "his", "her"
}

FOLLOWUP_PHRASES = [
    "give an example", "give me an example", "example of this", "explain more",
    "tell me more", "why so", "how so", "what about", "types of it", "previous one",
    "same topic", "above", "its advantages", "its disadvantages", "its types",
    "its features", "its applications", "how to use it", "why do we use it",
    "give example"
]


def is_follow_up_question(question: str) -> bool:
    """
    Fast, lightweight heuristic to check if a question is a follow-up.
    Returns True if the question contains pronouns or referential phrases.
    Returns False if the question is already standalone.
    """
    if not question:
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

    # Very short queries (< 4 words) without defining question starters like 'what is', 'explain', 'define'
    if len(words) <= 3 and not any(q_lower.startswith(prefix) for prefix in ["what is ", "explain ", "define ", "describe ", "list "]):
        return True

    return False


def rewrite_question_with_history(current_question: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Rewrites the latest user question into a standalone question using conversation history.
    
    If history is empty, missing, or question is already standalone, returns current_question unchanged immediately.
    """
    if not current_question or not current_question.strip():
        return current_question

    current_question_clean = current_question.strip()

    if not history:
        return current_question_clean

    # FAST PATH: Skip LLM call if question is standalone!
    if not is_follow_up_question(current_question_clean):
        print(f"[Contextualizer] Fast path: '{current_question_clean}' is standalone. Skipping LLM rewrite.")
        return current_question_clean

    # Format history for prompt (limit to recent 3 exchanges)
    history_lines = []
    for item in history[-3:]:
        q = item.get("question", "").strip()
        a = item.get("answer", "").strip()
        if q:
            history_lines.append(f"User: {q}")
        if a:
            history_lines.append(f"Assistant: {a[:200]}")

    conversation_history = "\n".join(history_lines).strip()
    if not conversation_history:
        return current_question_clean

    llm = get_llm()
    if not llm:
        print("[Contextualizer] LLM unavailable. Using original question.")
        return current_question_clean

    prompt = f"""You are a question contextualizer for VTUva, an AI study assistant.

Your task is to rewrite the user's latest question into a standalone question using the conversation history.

Rules:
- Do not answer the question.
- Do not add information that is not supported by the conversation.
- Resolve pronouns such as "it", "this", "that", "they", and "them" when the reference is clear.
- Resolve phrases such as "previous one", "same topic", "above", "explain more", "why", "how", and "give an example".
- If the question is already standalone, return it unchanged.
- Preserve the user's intent.
- Return ONLY the rewritten question.
- Do not add explanations or formatting.

Conversation history:
{conversation_history}

Latest user question:
{current_question_clean}
"""

    try:
        response = llm.invoke(prompt)
        rewritten = response.content.strip() if response and response.content else current_question_clean

        if rewritten.startswith('```') and rewritten.endswith('```'):
            rewritten = rewritten.strip('`').strip()
            if rewritten.startswith('python') or rewritten.startswith('text'):
                lines = rewritten.split('\n', 1)
                rewritten = lines[1] if len(lines) > 1 else rewritten
        
        rewritten = rewritten.strip('"\'')

        print("\n--- Question Contextualizer ---")
        print(f"Original question: {current_question_clean}")
        print(f"Rewritten question: {rewritten}")
        print("-------------------------------\n")

        return rewritten if rewritten else current_question_clean
    except Exception as e:
        print(f"[Contextualizer Error] Failed to rewrite question: {e}")
        return current_question_clean
