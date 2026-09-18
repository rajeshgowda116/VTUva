import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()


def get_chain(model_name: str = "gemini-1.5-flash"):
    """Return LangChain prompt | llm | parser sequence."""
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("⚠️ Warning: GOOGLE_API_KEY is not set.")

    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
        google_api_key=google_api_key
    )

    prompt = ChatPromptTemplate.from_template("""
You are VTUva, an AI assistant for VTU students.

Answer the student's question using ONLY the provided context.

If the answer is not available in the context, say:
"I couldn't find this information in the provided VTU documents."

Context:
{context}

Question:
{question}

Answer:
""")

    chain = prompt | llm | StrOutputParser()
    return chain