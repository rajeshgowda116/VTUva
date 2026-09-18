import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


load_dotenv()


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0
)


def generate_answer(question, context):

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

    response = llm.invoke(prompt)

    return response.content