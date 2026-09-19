from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.rag.pipeline import ask_question

app = FastAPI(title="VTUva API")


# Data model for JSON API requests
class QuestionRequest(BaseModel):
    question: str


@app.post("/ask")
def ask(question: str = Form(...)):
    """Handle Form submission requests."""
    answer = ask_question(question)
    return {"question": question, "answer": answer}


@app.post("/api/ask")
def ask_api(data: QuestionRequest):
    """Handle JSON API requests from frontend JavaScript."""
    answer = ask_question(data.question)
    return {"question": data.question, "answer": answer}


# Serve frontend index.html and static assets (styles.css, app.js) directly
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")