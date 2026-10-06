import os
import re
from typing import Generator
from dotenv import load_dotenv

load_dotenv()

_llm_instance = None


def get_llm(model_override: str = None):
    """
    Singleton lazy loader for LLM instance.
    Supports model_override parameter for fast contextualization.
    Supports LLM_PROVIDER=gemini | groq | ollama via environment variables.
    """
    global _llm_instance
    if model_override:
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if google_api_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model=model_override,
                    google_api_key=google_api_key.strip(),
                    temperature=0
                )
            except Exception:
                pass

    if _llm_instance is not None:
        return _llm_instance

    provider = os.getenv("LLM_PROVIDER", "").lower().strip()

    # 1. GOOGLE GEMINI API (Default High-Speed Cloud Provider)
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if (provider == "gemini" or not provider) and google_api_key and google_api_key.strip():
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            _llm_instance = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=google_api_key.strip(),
                temperature=0
            )

            print(f"[INIT] Gemini Fast LLM instance initialized ({model_name}).")
            return _llm_instance
        except Exception as e:
            print(f"[LLM Warning] Failed to initialize Gemini LLM: {e}")

    # 2. GROQ API (Alternative Cloud Provider)
    groq_api_key = os.getenv("GROQ_API_KEY")
    if (provider == "groq" or not provider) and groq_api_key and groq_api_key.strip():
        model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        try:
            from langchain_groq import ChatGroq
            _llm_instance = ChatGroq(
                model=model_name,
                groq_api_key=groq_api_key.strip(),
                temperature=0
            )
            print(f"[INIT] Groq LLM instance initialized with model '{model_name}'.")
            return _llm_instance
        except Exception as e:
            print(f"[LLM Warning] Failed to initialize Groq model '{model_name}': {e}.")

    # 3. OLLAMA LOCAL LLM
    if provider == "ollama" or os.getenv("OLLAMA_MODEL"):
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
        model_name = os.getenv("OLLAMA_MODEL", "llama3.2").strip()
        try:
            try:
                from langchain_ollama import ChatOllama
            except ImportError:
                from langchain_community.chat_models import ChatOllama

            _llm_instance = ChatOllama(
                base_url=base_url,
                model=model_name,
                temperature=0
            )
            print(f"[INIT] Ollama Local LLM initialized (Model: '{model_name}', Base URL: '{base_url}').")
            return _llm_instance
        except Exception as e:
            print(f"[LLM Warning] Failed to initialize Ollama LLM: {e}")

    return None


def build_prompt(question: str, context: str, subject: str = "General") -> str:
    """
    Subject-focused VTU RAG prompt builder with ChatGPT-style conversational directness
    and specialized answer modes (10-mark, 5-mark, notes, pyqs, comparisons, simple explanations).
    """
    q_lower = question.lower().strip()
    subj_code = subject.strip() if subject and subject.strip() and subject.strip() not in ("General", "All") else ""

    if subj_code:
        full_instruction = f"Please provide only {subj_code.lower()} subject answers only if he asked 5 marks explain 5 marks he asked 10 marks answer 10 marks explain simple way: {question}"
    else:
        full_instruction = f"Please provide only accurate VTU subject answers only if he asked 5 marks explain 5 marks he asked 10 marks answer 10 marks explain simple way: {question}"

    is_list_questions_mode = bool(re.search(
        r"\b(imp\s+questions?|important\s+questions?|most\s+imp|give\s+imp|list\s+questions?|show\s+questions?|pyqs?|repeated\s+questions?|frequently\s+asked)\b",
        q_lower
    )) and not bool(re.search(
        r"\b(explain\s+question|answer\s+question|solve|give\s+an?\s+answer|how\s+to\s+solve|10\s*marks?\s+answer|5\s*marks?\s+answer)\b",
        q_lower
    ))

    is_notes_mode = bool(re.search(r"\b(make\s+notes|create\s+notes|module\s*\d+\s*notes|syllabus\s+notes|notes\s+for)\b", q_lower))
    is_compare_mode = bool(re.search(r"\b(compare|difference\s+between|vs\.?|distinguish)\b", q_lower))
    is_5_marks = bool(re.search(r"\b(4\s*marks?|4\s*mark|5\s*marks?|5\s*mark|four\s*marks?|five\s*marks?)\b", q_lower))
    is_7_marks = bool(re.search(r"\b(6\s*marks?|6\s*mark|7\s*marks?|7\s*mark|six\s*marks?|seven\s*marks?)\b", q_lower))
    is_10_marks = bool(re.search(r"\b(8\s*marks?|8\s*mark|10\s*marks?|10\s*mark|eight\s*marks?|ten\s*marks?)\b", q_lower))
    is_short_def = bool(re.search(r"\b(define|what\s+is\s+a|what\s+is|short\s+note|definition)\b", q_lower)) and not (is_5_marks or is_10_marks or is_notes_mode or is_list_questions_mode)

    # 1. LIST IMPORTANT QUESTIONS MODE (QUESTIONS ONLY — NO DETAILED ANSWERS)
    if is_list_questions_mode:
        return f"""You are VTUva, an expert VTU Examination Assistant.

USER REQUEST: {question}
SUBJECT CODE: {subj_code if subj_code else 'VTU Subject'}

CRITICAL INSTRUCTIONS:
1. Output ONLY THE LIST OF IMPORTANT QUESTIONS. Do NOT generate full detailed answers, explanations, or solutions for each question.
2. Structure the output clearly using Markdown headers for each module (e.g. ### Module 1: [Module Title]).
3. Format each question on its OWN line as a numbered item with a bold mark weightage tag:
   1. **[10 Marks]** Question text...
   2. **[5 Marks]** Question text...
4. Make sure each question appears on a separate line with clean spacing.
5. End with this exact note:
   > 💡 *To get the step-by-step solution for any question above, simply ask "Explain Question 1" or "Give 10-mark answer for [Topic]".*

CONTEXT FROM VTU DOCUMENTS:
{context}

CLEAN STRUCTURED QUESTION LIST (QUESTIONS ONLY — NO LONG ANSWERS):
"""

    # 2. NOTES MODE
    if is_notes_mode:
        return f"""You are VTUva, an expert VTU Academic Assistant.

USER REQUEST:
{full_instruction}

STRICT CONSTRAINTS:
1. Start directly with the module notes title.
2. Structure the notes cleanly as follows:
   # Module — [Topic / Subject]
   ## Important Concepts
   - Bullet points of main concepts with bold terms.
   ## Key Definitions
   - Clear definitions of core terms.
   ## Important Questions
   - List of key exam questions for this module.
   ## Quick Revision
   - 3-4 bullet summary points for rapid revision.

CONTEXT FROM VTU DOCUMENTS:
{context}

MODULE NOTES:
"""

    # 2. PYQ / REPEATED QUESTIONS MODE
    if is_pyq_mode:
        return f"""You are VTUva, an expert VTU Previous Year Questions Evaluator.

USER REQUEST:
{full_instruction}

STRICT CONSTRAINTS:
1. Start directly with a clean markdown table of frequently asked questions.
2. Structure as follows:
   ## Frequently Asked Questions — {subj_code if subj_code else 'VTU Exam'}
   | Question | Weightage / Frequency | Key Focus Area |
   |---|---|---|
3. Only display frequency/years if present or supported by VTU document evidence.
4. Follow the table with 2-3 practical exam preparation tips.

CONTEXT FROM VTU DOCUMENTS:
{context}

PYQ SUMMARY:
"""

    # 3. COMPARISON MODE
    if is_compare_mode:
        return f"""You are VTUva, an expert VTU Academic Assistant.

USER REQUEST:
{full_instruction}

STRICT CONSTRAINTS:
1. Start directly with the comparison.
2. Use a clean Markdown table comparing the topics point-by-point (Definition, Working, Features, Applications, Key Differences).
3. Follow with a short concluding summary paragraph.

CONTEXT FROM VTU DOCUMENTS:
{context}

COMPARISON TABLE ANSWER:
"""

    # 4. 5-MARK EXAM MODE
    if is_5_marks:
        return f"""You are VTUva, an expert VTU Exam Assistant & Evaluator.

USER REQUEST:
{full_instruction}

STRICT CONSTRAINTS & 5-MARK STRUCTURE:
1. Start directly with the topic header: ## [Topic Title] (5-Mark Response)
2. **Definition / Overview**: 2-3 clear, concise sentences in plain English.
3. **5 Core Key Points**: 5 numbered points with **bold terms** explained simply.
4. **Simple ASCII Diagram / Flowchart**: Clean block diagram if applicable.
5. **Key Applications / Features**: Short bullet points.
6. Conclude with: > *Note: This answer is structured for a 5-mark VTU-style response.*

CONTEXT FROM VTU DOCUMENTS:
{context}

5-MARK VTU EXAM ANSWER:
"""

    # 5. 10-MARK EXAM MODE
    if is_7_marks or is_10_marks:
        marks_label = "7-MARK" if is_7_marks else "10-MARK"
        return f"""You are VTUva, an expert VTU Exam Assistant & Evaluator.

USER REQUEST:
{full_instruction}

STRICT CONSTRAINTS & {marks_label} STRUCTURE:
1. Start directly with the topic header: ## [Topic Title] ({marks_label} Response)
2. **Definition & Introduction**: Clear introductory section explaining the core concept.
3. **Architecture / Structural Diagram**: Labeled ASCII diagram or flowchart breakdown.
4. **Detailed Components & Working Principle**:
   - Numbered/bulleted sections for all core components with **bold keywords**.
   - Step-by-step explanation of working procedure.
5. **Practical Applications & Real-World Use**: Specific engineering applications.
6. **Key Advantages & Limitations**: Bullet points or simple summary table.
7. Conclude with: > *Note: This answer is structured for a {marks_label.lower()} VTU-style response.*

CONTEXT FROM VTU DOCUMENTS:
{context}

{marks_label} VTU EXAM ANSWER:
"""

    # 6. SHORT DEFINITION / DEFAULT NATURAL RESPONSE
    if is_short_def:
        return f"""You are VTUva, a conversational VTU Academic Assistant.

USER REQUEST:
{full_instruction}

STRICT CONSTRAINTS:
1. Start directly with a clear, concise definition (2-4 sentences).
2. Follow with 3-4 bullet points highlighting key characteristics or applications.
3. Do NOT add conversational preamble or filler.

CONTEXT FROM VTU DOCUMENTS:
{context}

CONCISE DEFINITION ANSWER:
"""

    # 7. GENERAL CONVERSATIONAL EXPLANATION
    return f"""You are VTUva, a professional, conversational VTU Academic Assistant (ChatGPT-style response).

USER REQUEST:
{full_instruction}

STRICT CONSTRAINTS:
1. Start directly with the answer. Avoid preamble (e.g. "Sure, I can help").
2. Use Markdown formatting: headings (##, ###), bold key terms, bullet points, short readable paragraphs, code blocks, and clear math formatting.
3. Keep the length proportional to what the user asked (concise for simple questions, thorough for detailed questions).
4. Strictly ground facts in the retrieved VTU context without inventing unverified syllabus details.

CONTEXT FROM VTU DOCUMENTS:
{context}

NATURAL VTU RESPONSE:
"""


def extract_text_from_chunk(chunk) -> str:
    if not chunk:
        return ""
    content = getattr(chunk, "content", chunk)
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("text"):
                parts.append(item["text"])
        return "".join(parts)
    return str(content) if content else ""


def generate_answer(question: str, context: str, subject: str = "General") -> str:
    if not context or not context.strip():
        return "This topic is not present in the ingested VTU syllabus/notes documents."

    google_api_key = os.getenv("GOOGLE_API_KEY")
    if google_api_key and google_api_key.strip():
        try:
            import google.genai as genai
            client = genai.Client(api_key=google_api_key.strip())
            prompt = build_prompt(question, context, subject=subject)
            models = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash-lite", "gemini-1.5-flash-8b"]
            for m in models:
                try:
                    res = client.models.generate_content(model=m, contents=prompt)
                    if res and res.text:
                        return res.text.strip()
                except Exception as m_err:
                    print(f"[Fast Fallback] Model '{m}' failed/rate-limited: {m_err}. Trying next model...")
                    continue
        except Exception as genai_err:
            print(f"[GenAI Client Error] Fallback to LangChain LLM: {genai_err}")

    llm = get_llm()
    if not llm:
        return (
            "⚠️ **LLM Provider Configuration Missing**\n\n"
            "Please set `GOOGLE_API_KEY` in your `.env` file.\n\n"
            "**Retrieved Context Snippet:**\n"
            f"{context[:400]}..."
        )

    prompt = build_prompt(question, context, subject=subject)
    try:
        response = llm.invoke(prompt)
        return extract_text_from_chunk(response)
    except Exception as e:
        return f"⚠️ Error generating answer: {e}"


def generate_answer_stream(question: str, context: str, subject: str = "General") -> Generator[str, None, None]:
    """Yields generated tokens one by one with fast zero-sleep fallback."""
    if not context or not context.strip():
        yield "This topic is not present in the ingested VTU syllabus/notes documents."
        return

    google_api_key = os.getenv("GOOGLE_API_KEY")
    if google_api_key and google_api_key.strip():
        try:
            import google.genai as genai
            client = genai.Client(api_key=google_api_key.strip())
            prompt = build_prompt(question, context, subject=subject)
            models = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash-lite", "gemini-1.5-flash-8b"]
            
            for m in models:
                try:
                    res_stream = client.models.generate_content_stream(model=m, contents=prompt)
                    has_tokens = False
                    for chunk in res_stream:
                        if chunk.text:
                            has_tokens = True
                            yield chunk.text
                    if has_tokens:
                        return
                except Exception as m_err:
                    print(f"[Fast Stream Fallback] Model '{m}' rate-limited/failed: {m_err}. Switching immediately...")
                    continue
        except Exception as genai_err:
            print(f"[GenAI Direct Stream Error] Fallback to LangChain LLM: {genai_err}")

    llm = get_llm()
    if not llm:
        yield "⚠️ **LLM Provider Configuration Missing**: Please set `GOOGLE_API_KEY` in `.env`."
        return

    prompt = build_prompt(question, context, subject=subject)
    try:
        for chunk in llm.stream(prompt):
            text_chunk = extract_text_from_chunk(chunk)
            if text_chunk:
                yield text_chunk
    except Exception as e:
        yield f"\n\n⚠️ Error generating stream from LLM: {e}"