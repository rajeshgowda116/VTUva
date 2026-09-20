import os
import sys
from pathlib import Path

# Add project root and backend folder to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any

try:
    from backend.rag.pipeline import ask_question
except ImportError:
    from rag.pipeline import ask_question

app = FastAPI(title="VTUva API")

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QuestionRequest(BaseModel):
    question: str


@app.get("/api/health")
def health_check():
    return {"status": "online", "message": "VTUva Backend API is running"}


@app.post("/ask")
@app.post("/api/ask")
def ask_api(data: QuestionRequest):
    """Handle JSON API requests from frontend JavaScript."""
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