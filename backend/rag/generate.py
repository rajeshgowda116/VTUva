import os
from typing import Generator
from dotenv import load_dotenv

load_dotenv()

_llm_instance = None


def get_llm():
    """Singleton lazy loader for LLM instance (Groq ChatGroq primary, Gemini fallback)."""
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance

    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key and groq_api_key.strip():
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
            print(f"[LLM Warning] Failed to initialize Groq model '{model_name}': {e}. Retrying with 'qwen/qwen3.8-27b'...")
            try:
                from langchain_groq import ChatGroq
                _llm_instance = ChatGroq(
                    model="qwen/qwen3.8-27b",
                    groq_api_key=groq_api_key.strip(),
                    temperature=0
                )
                print("[INIT] Groq LLM instance initialized with model 'qwen/qwen3.8-27b'.")
                return _llm_instance
            except Exception as e2:
                print(f"[LLM Warning] Groq fallback failed: {e2}")

    # Fallback to Google Gemini
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if google_api_key and google_api_key.strip():
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            _llm_instance = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=google_api_key.strip(),
                temperature=0
            )
            print("[INIT] Gemini LLM instance initialized (Fallback).")
            return _llm_instance
        except Exception as e:
            print(f"[LLM Warning] Failed to initialize Gemini LLM: {e}")

    return None


def build_prompt(question: str, context: str) -> str:
    return f"""You are VTUva, a VTU engineering study assistant.

Answer the student's question using the information in CONTEXT.

The student wants an exam-oriented answer.

For a 10-mark question:
- Give a clear introduction
- Explain the important points
- Include working/principle if available
- Include equations/reactions if available in the context
- Use headings and bullet points
- Do not invent information

If the context does not contain enough information, say so clearly.

CONTEXT:
{context}

STUDENT QUESTION:
{question}

ANSWER:
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


def generate_answer(question: str, context: str) -> str:
    llm = get_llm()
    if not llm:
        return (
            "⚠️ **API Key Missing**\n\n"
            "Please set `GROQ_API_KEY` (or `GOOGLE_API_KEY`) in your `.env` file to enable AI answer generation.\n\n"
            "**Retrieved Context Snippet:**\n"
            f"{context[:400]}..."
        )

    prompt = build_prompt(question, context)

    try:
        response = llm.invoke(prompt)
        return extract_text_from_chunk(response)
    except Exception as e:
        return f"⚠️ Error generating answer from LLM API: {str(e)}"


def generate_answer_stream(question: str, context: str) -> Generator[str, None, None]:
    """Yields generated tokens one by one as they arrive from the LLM."""
    llm = get_llm()
    if not llm:
        yield (
            "⚠️ **API Key Missing**\n\n"
            "Please set `GROQ_API_KEY` in your `.env` file at the root of the project."
        )
        return

    prompt = build_prompt(question, context)

    try:
        for chunk in llm.stream(prompt):
            text_chunk = extract_text_from_chunk(chunk)
            if text_chunk:
                yield text_chunk
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "rate_limit" in err_msg.lower():
            yield "\n\n⚠️ **Groq API Rate Limit Reached (429)**: Free tier limit reached. Please retry in a few seconds."
        else:
            yield f"\n\n⚠️ Error generating stream from Groq API: {err_msg}"