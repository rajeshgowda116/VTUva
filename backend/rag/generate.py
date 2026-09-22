import os
from typing import Generator
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

_llm_instance = None


def get_llm():
    """Singleton lazy loader for ChatGoogleGenerativeAI instance."""
    global _llm_instance
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    if _llm_instance is None:
        _llm_instance = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0
        )
        print("[INIT] Gemini 2.5 Flash LLM instance initialized.")
    return _llm_instance


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


def generate_answer(question: str, context: str) -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return (
            "⚠️ **Gemini API Key Missing**\n\n"
            "Please set your `GOOGLE_API_KEY` in the `.env` file at the root of the project to enable AI answer generation.\n\n"
            "**Retrieved Context Snippet:**\n"
            f"{context[:400]}..."
        )

    llm = get_llm()
    if not llm:
        return "⚠️ Unable to initialize Gemini LLM. Please check your GOOGLE_API_KEY configuration."

    prompt = build_prompt(question, context)

    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"⚠️ Error generating answer from Gemini API: {str(e)}"


def generate_answer_stream(question: str, context: str) -> Generator[str, None, None]:
    """Yields generated tokens one by one as they arrive from Gemini."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        yield (
            "⚠️ **Gemini API Key Missing**\n\n"
            "Please set your `GOOGLE_API_KEY` in the `.env` file at the root of the project."
        )
        return

    llm = get_llm()
    if not llm:
        yield "⚠️ Unable to initialize Gemini LLM. Please check your GOOGLE_API_KEY configuration."
        return

    prompt = build_prompt(question, context)

    try:
        for chunk in llm.stream(prompt):
            if chunk and chunk.content:
                yield chunk.content
    except Exception as e:
        yield f"\n\n⚠️ Error generating stream from Gemini API: {str(e)}"