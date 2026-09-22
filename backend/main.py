import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

# Add project root and backend folder to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from sqlalchemy.orm import Session

try:
    from backend.database import engine, Base, get_db, SessionLocal
    from backend.models import ChatHistory
    from backend.schemas import ChatRequest, ChatResponse
    from backend.rag.pipeline import ask_question, prepare_rag_context
    from backend.rag.generate import generate_answer_stream, get_llm
    from backend.rag.retriever import get_retriever, get_vector_store
    from backend.rag.embeddings import get_embeddings
except ImportError:
    from database import engine, Base, get_db, SessionLocal
    from models import ChatHistory
    from schemas import ChatRequest, ChatResponse
    from rag.pipeline import ask_question, prepare_rag_context
    from rag.generate import generate_answer_stream, get_llm
    from rag.retriever import get_retriever, get_vector_store
    from rag.embeddings import get_embeddings

# Create database tables if they do not exist
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"[DB Warning] Could not auto-create database tables: {e}")


import asyncio

def warmup_models():
    print("\n==================================================")
    print(" PRE-WARMING VTUVA RAG SINGLETON MODELS (BACKGROUND)")
    print("==================================================")
    t_boot = time.perf_counter()
    try:
        get_embeddings()
        get_vector_store()
        get_retriever(k=4)
        get_llm()
        print(f"[WARMUP COMPLETE] All models pre-loaded in {time.perf_counter() - t_boot:.2f}s")
    except Exception as e:
        print(f"[WARMUP WARNING] Pre-warming incomplete: {e}")
    print("==================================================\n")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup handler - launches background model pre-warming so server opens port 8000 instantly."""
    asyncio.create_task(asyncio.to_thread(warmup_models))
    yield


app = FastAPI(title="VTUva API", lifespan=lifespan)

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


@app.post("/api/chat/stream")
def post_chat_stream(data: ChatRequest, request: Request, db: Session = Depends(get_db)):
    """Streaming endpoint for fast Time-to-First-Token and progressive answer generation."""
    if not data.question or not data.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    user_id_header = request.headers.get("X-User-ID", "1")
    try:
        user_id = int(user_id_header)
    except ValueError:
        user_id = 1

    question_text = data.question.strip()

    def event_generator():
        t_start = time.perf_counter()

        # 1. Fetch recent chat history from SQL (last 3 exchanges)
        t_hist_start = time.perf_counter()
        recent_records = (
            db.query(ChatHistory)
            .filter(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.id.desc())
            .limit(3)
            .all()
        )
        recent_records.reverse()
        history = [
            {"question": record.question, "answer": record.answer}
            for record in recent_records
        ]
        t_hist = time.perf_counter() - t_hist_start

        # 2. Context rewriting & Vector Search (k=4)
        standalone_question, sources, context, t_rewrite, t_vector = prepare_rag_context(
            question_text, history=history
        )

        # Send initial metadata (sources) immediately
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources, 'standalone_question': standalone_question})}\n\n"

        if not context:
            no_info_msg = "No relevant information found in the VTU documents."
            yield f"data: {json.dumps({'type': 'token', 'token': no_info_msg})}\n\n"
            
            # Save record to SQL
            chat_record = ChatHistory(
                user_id=user_id,
                question=question_text,
                answer=no_info_msg,
                created_at=datetime.utcnow()
            )
            db.add(chat_record)
            db.commit()
            yield f"data: {json.dumps({'type': 'done', 'id': chat_record.id})}\n\n"
            return

        # 3. Stream LLM Answer Generation
        full_answer_chunks = []
        t_first_token = None
        t_llm_start = time.perf_counter()

        for chunk in generate_answer_stream(standalone_question, context):
            if t_first_token is None:
                t_first_token = time.perf_counter() - t_start

            full_answer_chunks.append(chunk)
            yield f"data: {json.dumps({'type': 'token', 'token': chunk})}\n\n"

        t_llm_total = time.perf_counter() - t_llm_start
        t_db_start = time.perf_counter()

        full_answer = "".join(full_answer_chunks)

        # 4. Save COMPLETE answer to SQL ONCE after generation completes
        try:
            chat_record = ChatHistory(
                user_id=user_id,
                question=question_text,
                answer=full_answer,
                created_at=datetime.utcnow()
            )
            db.add(chat_record)
            db.commit()
            db.refresh(chat_record)
            record_id = chat_record.id
        except Exception as db_err:
            db.rollback()
            print(f"[DB Error] Failed to save chat record: {db_err}")
            record_id = 0

        t_db = time.perf_counter() - t_db_start
        t_total = time.perf_counter() - t_start

        ttft_str = f"{t_first_token:.3f}s" if t_first_token is not None else "N/A"
        print(f"\n[STREAM PERF TIMING]\n"
              f"  - History Retrieval : {t_hist:.3f}s\n"
              f"  - Context Rewriting : {t_rewrite:.3f}s\n"
              f"  - Vector Search(k=4): {t_vector:.3f}s\n"
              f"  - First-Token (TTFT): {ttft_str}\n"
              f"  - LLM Full Stream   : {t_llm_total:.3f}s\n"
              f"  - SQL Save          : {t_db:.3f}s\n"
              f"  - TOTAL REQUEST TIME: {t_total:.3f}s\n")

        yield f"data: {json.dumps({'type': 'done', 'id': record_id})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/chat", response_model=ChatResponse)
def post_chat(data: ChatRequest, request: Request, db: Session = Depends(get_db)):
    """Standard non-streaming endpoint fallback."""
    if not data.question or not data.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    user_id_header = request.headers.get("X-User-ID", "1")
    try:
        user_id = int(user_id_header)
    except ValueError:
        user_id = 1

    try:
        recent_records = (
            db.query(ChatHistory)
            .filter(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.id.desc())
            .limit(3)
            .all()
        )
        recent_records.reverse()
        history = [
            {"question": record.question, "answer": record.answer}
            for record in recent_records
        ]

        result = ask_question(data.question.strip(), history=history)
        answer_text = result.get("answer", "") if isinstance(result, dict) else str(result)
        sources = result.get("sources", []) if isinstance(result, dict) else []

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

# Serve frontend static assets
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