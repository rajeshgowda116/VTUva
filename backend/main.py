import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root and backend folder to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from sqlalchemy.orm import Session

try:
    from backend.database import engine, Base, get_db
    from backend.models import ChatHistory
    from backend.schemas import ChatRequest, ChatResponse
    from backend.rag.pipeline import ask_question
except ImportError:
    from database import engine, Base, get_db
    from models import ChatHistory
    from schemas import ChatRequest, ChatResponse
    from rag.pipeline import ask_question

# Create database tables if they do not exist
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"[DB Warning] Could not auto-create database tables: {e}")

app = FastAPI(title="VTUva API")

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {"status": "online", "message": "VTUva Backend API is running"}


@app.post("/api/chat", response_model=ChatResponse)
def post_chat(data: ChatRequest, request: Request, db: Session = Depends(get_db)):
    """
    1. Receive the user's question.
    2. Send it to the existing RAG/LLM.
    3. Get the generated answer.
    4. Save question + answer + user_id + timestamp into MySQL.
    5. Return the saved record to the frontend.
    """
    if not data.question or not data.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Extract user_id from header (default to 1)
    user_id_header = request.headers.get("X-User-ID", "1")
    try:
        user_id = int(user_id_header)
    except ValueError:
        user_id = 1

    try:
        # Call existing RAG pipeline
        result = ask_question(data.question.strip())
        if isinstance(result, str):
            answer_text = result
            sources = []
        else:
            answer_text = result.get("answer", "")
            sources = result.get("sources", [])

        # Create record in MySQL
        chat_record = ChatHistory(
            user_id=user_id,
            question=data.question.strip(),
            answer=answer_text,
            created_at=datetime.utcnow()
        )
        db.add(chat_record)
        db.commit()
        db.refresh(chat_record)

        return ChatResponse(
            id=chat_record.id,
            question=chat_record.question,
            answer=chat_record.answer,
            created_at=chat_record.created_at,
            sources=sources
        )
    except Exception as e:
        db.rollback()
        print(f"Error in /api/chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/history", response_model=List[ChatResponse])
def get_chat_history(request: Request, db: Session = Depends(get_db)):
    """
    Returns the logged-in user's previous questions and answers from MySQL.
    """
    user_id_header = request.headers.get("X-User-ID", "1")
    try:
        user_id = int(user_id_header)
    except ValueError:
        user_id = 1

    try:
        history = (
            db.query(ChatHistory)
            .filter(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.id.asc())
            .all()
        )
        return history
    except Exception as e:
        print(f"Error in /api/chat/history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask")
@app.post("/api/ask")
def ask_api(data: ChatRequest):
    """Legacy route compatibility."""
    try:
        result = ask_question(data.question)
        if isinstance(result, str):
            return {"question": data.question, "answer": result, "sources": []}
        return {
            "question": data.question,
            "answer": result.get("answer", ""),
            "sources": result.get("sources", [])
        }
    except Exception as e:
        print(f"Error processing question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Serve document PDF static assets
data_dir = ROOT_DIR / "data"
if data_dir.exists():
    app.mount("/data", StaticFiles(directory=str(data_dir)), name="data")

# Serve frontend static assets cleanly without overriding API POST routes
frontend_dir = ROOT_DIR / "frontend"
if frontend_dir.exists():
    @app.get("/")
    async def serve_index():
        return FileResponse(frontend_dir / "index.html")

    @app.get("/{file_name}")
    async def serve_frontend_files(file_name: str):
        file_path = frontend_dir / file_name
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dir / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)