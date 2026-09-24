import os
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
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
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
            "⚠️ **LLM Provider Configuration Missing**\n\n"
            "Please set `GOOGLE_API_KEY` in your `.env` file.\n\n"
            "**Retrieved Context Snippet:**\n"
            f"{context[:400]}..."
        )

    prompt = build_prompt(question, context)

    try:
        response = llm.invoke(prompt)
        return extract_text_from_chunk(response)
    except Exception as e:
        err_msg = str(e)
        if "connection" in err_msg.lower() or "connect" in err_msg.lower() or "11434" in err_msg:
            return f"⚠️ **Ollama Connection Error**: Could not connect to local Ollama server at `{os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}`."
        return f"⚠️ Error generating answer from LLM API: {err_msg}"


def generate_answer_stream(question: str, context: str) -> Generator[str, None, None]:
    """Yields generated tokens one by one as they arrive from the LLM."""
    llm = get_llm()
    if not llm:
        yield (
            "⚠️ **LLM Provider Configuration Missing**\n\n"
            "Please set `GOOGLE_API_KEY` in your `.env` file at the root of the project."
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
        if "connection" in err_msg.lower() or "connect" in err_msg.lower() or "11434" in err_msg:
            yield f"\n\n⚠️ **Ollama Connection Error**: Could not connect to local Ollama server at `{os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}`."
        elif "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "rate_limit" in err_msg.lower():
            yield "\n\n⚠️ **API Rate Limit Reached (429)**: Free tier limit reached. Please retry in a few seconds."
        else:
            yield f"\n\n⚠️ Error generating stream from LLM: {err_msg}"