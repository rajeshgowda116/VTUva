import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


def get_llm():
    """Lazily load ChatGoogleGenerativeAI instance."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0
    )


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

    prompt = f"""
You are VTUva, a VTU engineering study assistant.

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

    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"⚠️ Error generating answer from Gemini API: {str(e)}"