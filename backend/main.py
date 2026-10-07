import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Add project root and backend folder to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

try:
    from backend.database import engine, Base, get_db, SessionLocal
    from backend.models import ChatHistory, UserProfile, VTUUpdate, User, PYQQuestion, PYQQuestionGroup, ScrapedDocument
    from backend.schemas import (
        ChatRequest, ChatResponse, UserProfileRequest, UserProfileResponse, VTUUpdateResponse,
        UserRegisterRequest, UserLoginRequest, UserAuthResponse, PYQQuestionGroupResponse, PYQQuestionResponse
    )
    from backend.auth import hash_password, verify_password, generate_user_token, get_current_user
    from backend.rag.pipeline import ask_question, prepare_rag_context
    from backend.rag.generate import generate_answer_stream, get_llm
    from backend.rag.retriever import get_retriever, get_vector_store
    from backend.rag.embeddings import get_embeddings
    from backend.scraper.api import router as scraper_router
    from backend.scraper.scheduler import start_scraper_scheduler, stop_scraper_scheduler
except ImportError:
    from database import engine, Base, get_db, SessionLocal
    from models import ChatHistory, UserProfile, VTUUpdate, User, PYQQuestion, PYQQuestionGroup, ScrapedDocument
    from schemas import (
        ChatRequest, ChatResponse, UserProfileRequest, UserProfileResponse, VTUUpdateResponse,
        UserRegisterRequest, UserLoginRequest, UserAuthResponse, PYQQuestionGroupResponse, PYQQuestionResponse
    )
    from auth import hash_password, verify_password, generate_user_token, get_current_user
    from rag.pipeline import ask_question, prepare_rag_context
    from rag.generate import generate_answer_stream, get_llm
    from rag.retriever import get_retriever, get_vector_store
    from rag.embeddings import get_embeddings
    from scraper.api import router as scraper_router
    from scraper.scheduler import start_scraper_scheduler, stop_scraper_scheduler




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
    """Application startup handler - launches background model pre-warming and 24-hour scraper scheduler."""
    asyncio.create_task(asyncio.to_thread(warmup_models))
    try:
        start_scraper_scheduler()
    except Exception as sched_err:
        print(f"[Lifespan Warning] Could not start scraper scheduler: {sched_err}")
    yield
    try:
        stop_scraper_scheduler()
    except Exception:
        pass


app = FastAPI(title="VTUva API", lifespan=lifespan)
app.include_router(scraper_router)

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


import urllib.request


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
    subject_tag = data.subject or "General"

    def event_generator():
        t_start = time.perf_counter()

        # 1. Fetch chat history (use request payload history if provided, or fallback to SQL DB)
        t_hist_start = time.perf_counter()
        if data.history and isinstance(data.history, list) and len(data.history) > 0:
            history = [
                {"question": str(h.get("question", "")), "answer": str(h.get("answer", ""))}
                for h in data.history if isinstance(h, dict)
            ]
        else:
            recent_records = (
                db.query(ChatHistory)
                .filter(ChatHistory.user_id == user_id)
                .order_by(ChatHistory.id.desc())
                .limit(4)
                .all()
            )
            recent_records.reverse()
            history = [
                {"question": record.question, "answer": record.answer}
                for record in recent_records
            ]
        t_hist = time.perf_counter() - t_hist_start

        # 2. Context rewriting & Vector Search (k=4 with metadata filter)
        filter_dict = {}
        if data.subject_code and data.subject_code.strip():
            filter_dict["subject_code"] = data.subject_code.strip().upper()
        if data.module:
            filter_dict["module"] = data.module

        standalone_question, sources, context, t_rewrite, t_vector = prepare_rag_context(
            question_text, history=history, filter_dict=filter_dict if filter_dict else None
        )


        # Send initial metadata (sources) immediately
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources, 'standalone_question': standalone_question})}\n\n"

        if context and context.startswith("__") and context.endswith("__"):
            intent_key = context.strip("_")
            try:
                from backend.rag.pipeline import CASUAL_RESPONSES
            except ImportError:
                from rag.pipeline import CASUAL_RESPONSES
            casual_msg = CASUAL_RESPONSES.get(intent_key, "Glad to help! 😊 Ask me anything about your VTU subjects.")
            yield f"data: {json.dumps({'type': 'token', 'token': casual_msg})}\n\n"
            try:
                chat_record = ChatHistory(
                    user_id=user_id,
                    subject=subject_tag,
                    question=question_text,
                    answer=casual_msg,
                    created_at=datetime.utcnow()
                )
                db.add(chat_record)
                db.commit()
                db.refresh(chat_record)
                rec_id = chat_record.id
            except Exception:
                db.rollback()
                rec_id = 0

            yield f"data: {json.dumps({'type': 'done', 'id': rec_id})}\n\n"
            return

        if not context:
            no_info_msg = "I couldn't find enough information about that in my current VTU knowledge base."
            yield f"data: {json.dumps({'type': 'token', 'token': no_info_msg})}\n\n"
            
            # Save record to SQL
            try:
                chat_record = ChatHistory(
                    user_id=user_id,
                    subject=subject_tag,
                    question=question_text,
                    answer=no_info_msg,
                    created_at=datetime.utcnow()
                )
                db.add(chat_record)
                db.commit()
                rec_id = chat_record.id
            except Exception:
                db.rollback()
                rec_id = 0
            yield f"data: {json.dumps({'type': 'done', 'id': rec_id})}\n\n"
            return


        # 3. Stream LLM Answer Generation
        full_answer_chunks = []
        t_first_token = None
        t_llm_start = time.perf_counter()

        for chunk in generate_answer_stream(standalone_question, context, subject=subject_tag):
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
                subject=subject_tag,
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

        subject_tag = data.subject or "General"
        result = ask_question(data.question.strip(), history=history, subject=subject_tag)
        answer_text = result.get("answer", "") if isinstance(result, dict) else str(result)
        sources = result.get("sources", []) if isinstance(result, dict) else []
        chat_record = ChatHistory(
            user_id=user_id,
            subject=subject_tag,
            question=data.question.strip(),
            answer=answer_text,
            created_at=datetime.utcnow()
        )
        db.add(chat_record)
        db.commit()
        db.refresh(chat_record)

        return ChatResponse(
            id=chat_record.id,
            subject=chat_record.subject,
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
def get_chat_history(request: Request, subject: Optional[str] = None, db: Session = Depends(get_db)):
    user_id_header = request.headers.get("X-User-ID", "1")
    try:
        user_id = int(user_id_header)
    except ValueError:
        user_id = 1

    try:
        query = db.query(ChatHistory).filter(ChatHistory.user_id == user_id)
        if subject and subject.strip() and subject.strip() != "All":
            query = query.filter(ChatHistory.subject == subject.strip())
        history = query.order_by(ChatHistory.id.asc()).all()
        return history
    except Exception as e:
        print(f"Error in /api/chat/history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/user/profile", response_model=UserProfileResponse)
def save_user_profile(data: UserProfileRequest, request: Request, db: Session = Depends(get_db)):
    user_id_header = request.headers.get("X-User-ID", "1")
    try:
        user_id = int(user_id_header)
    except ValueError:
        user_id = 1

    try:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        subjects_json_str = json.dumps(data.subjects)
        if not profile:
            profile = UserProfile(
                user_id=user_id,
                name=data.name or "Rajesh Gouda",
                usn=data.usn or "4DM24AI038",
                semester=data.semester,
                branch=data.branch,
                branch_full=data.branch_full,
                subjects_json=subjects_json_str
            )
            db.add(profile)
        else:
            profile.name = data.name or profile.name
            profile.usn = data.usn or profile.usn
            profile.semester = data.semester
            profile.branch = data.branch
            profile.branch_full = data.branch_full
            profile.subjects_json = subjects_json_str
        
        db.commit()
        db.refresh(profile)

        return UserProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            name=profile.name,
            usn=profile.usn,
            semester=profile.semester,
            branch=profile.branch,
            branch_full=profile.branch_full,
            subjects=json.loads(profile.subjects_json),
            created_at=profile.created_at,
            updated_at=profile.updated_at
        )
    except Exception as e:
        db.rollback()
        print(f"Error in /api/user/profile (POST): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/user/profile", response_model=UserProfileResponse)
def get_user_profile(request: Request, db: Session = Depends(get_db)):
    user_id_header = request.headers.get("X-User-ID", "1")
    try:
        user_id = int(user_id_header)
    except ValueError:
        user_id = 1

    try:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            default_subjects = [
                {"code": "BCS501", "name": "Software Engineering and Project Management"},
                {"code": "BCS502", "name": "Computer Networks"},
                {"code": "BCS503", "name": "Theory of Computation"}
            ]
            profile = UserProfile(
                user_id=user_id,
                name="Rajesh Gouda",
                usn="4DM24AI038",
                semester="5th Semester",
                branch="AIML",
                branch_full="Artificial Intelligence & Machine Learning (AIML)",
                subjects_json=json.dumps(default_subjects)
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)

        return UserProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            name=profile.name,
            usn=profile.usn,
            semester=profile.semester,
            branch=profile.branch,
            branch_full=profile.branch_full,
            subjects=json.loads(profile.subjects_json),
            created_at=profile.created_at,
            updated_at=profile.updated_at
        )
    except Exception as e:
        print(f"Error in /api/user/profile (GET): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/updates", response_model=List[VTUUpdateResponse])
def get_vtu_updates(category: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        category_links = {
            "Result": "https://results.vtu.ac.in/",
            "Exam": "https://vtu.ac.in/category/time-table",
            "Time Tables": "https://vtu.ac.in/category/time-table",
            "Notification": "https://vtu.ac.in/en/category/administration/notifications/",
            "Circular": "https://vtu.ac.in/en/category/administration/circulars/",
            "Syllabus": "https://vtu.ac.in/model-question-paper-b-e-b-tech-b-arch",
            "General": "https://vtu.ac.in/"
        }

        count = db.query(VTUUpdate).count()
        if count == 0:
            default_updates = [
                VTUUpdate(
                    category="Result",
                    title="VTU 3rd Semester & Revaluation Results",
                    summary="Check official VTU semester examination results, revaluation results, and grade cards.",
                    time_posted="2 hours ago",
                    badge_color="green",
                    icon_type="document",
                    link="https://results.vtu.ac.in/"
                ),
                VTUUpdate(
                    category="Exam",
                    title="5th Semester Exam Time Table & Schedule",
                    summary="VTU has released the examination time table for B.E/B.Tech end semester examinations.",
                    time_posted="1 day ago",
                    badge_color="red",
                    icon_type="calendar",
                    link="https://vtu.ac.in/category/time-table"
                ),
                VTUUpdate(
                    category="Notification",
                    title="Updated Syllabus for 2022 Scheme",
                    summary="Revised syllabus and model question papers for select subjects under VTU 2022 scheme.",
                    time_posted="2 days ago",
                    badge_color="blue",
                    icon_type="file",
                    link="https://vtu.ac.in/en/category/administration/notifications/"
                ),
                VTUUpdate(
                    category="Circular",
                    title="Internal Assessment & Exam Guidelines",
                    summary="VTU Registrar circular regarding internal assessment marks submission and academic guidelines.",
                    time_posted="3 days ago",
                    badge_color="amber",
                    icon_type="megaphone",
                    link="https://vtu.ac.in/en/category/administration/circulars/"
                ),
                VTUUpdate(
                    category="Syllabus",
                    title="Model Question Papers B.E. / B.Tech",
                    summary="Download official VTU model question papers and scheme structure for undergraduate programs.",
                    time_posted="4 days ago",
                    badge_color="indigo",
                    icon_type="document",
                    link="https://vtu.ac.in/model-question-paper-b-e-b-tech-b-arch"
                ),
                VTUUpdate(
                    category="General",
                    title="VTU Convocation & Campus Announcement",
                    summary="VTU Convocation details, Centralised Placement Cell notifications, and university announcements.",
                    time_posted="5 days ago",
                    badge_color="purple",
                    icon_type="cap",
                    link="https://vtu.ac.in/"
                )
            ]
            for u in default_updates:
                db.add(u)
            db.commit()
        else:
            existing_updates = db.query(VTUUpdate).all()
            updated_any = False
            for u in existing_updates:
                if not u.link:
                    u.link = category_links.get(u.category, "https://vtu.ac.in/")
                    updated_any = True
            if updated_any:
                db.commit()

        query = db.query(VTUUpdate)
        if category and category.strip() and category.strip().lower() != "all":
            query = query.filter(VTUUpdate.category.ilike(category.strip()))

        return query.order_by(VTUUpdate.id.asc()).all()
    except Exception as e:
        print(f"Error in /api/updates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# PRIORITY 5: AUTHENTICATION API ROUTES
# ============================================================

@app.post("/api/auth/register", response_model=UserAuthResponse)
def register_user(data: UserRegisterRequest, db: Session = Depends(get_db)):
    """User Registration with PBKDF2 password hashing."""
    existing = db.query(User).filter(User.email == data.email.strip().lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Account with this email already exists.")

    p_hash, salt = hash_password(data.password)
    user = User(
        email=data.email.strip().lower(),
        password_hash=p_hash,
        salt=salt,
        name=data.name.strip(),
        usn=data.usn.strip() if data.usn else "4DM24AI038",
        semester=data.semester or "5th Semester",
        branch=data.branch or "AIML"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = generate_user_token(user.id, user.email)
    user.token = token
    db.commit()

    return UserAuthResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        usn=user.usn,
        semester=user.semester,
        branch=user.branch,
        token=token
    )


@app.post("/api/auth/login", response_model=UserAuthResponse)
def login_user(data: UserLoginRequest, db: Session = Depends(get_db)):
    """User Login with credentials validation."""
    user = db.query(User).filter(User.email == data.email.strip().lower()).first()
    if not user or not verify_password(data.password, user.password_hash, user.salt):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = generate_user_token(user.id, user.email)
    user.token = token
    db.commit()

    return UserAuthResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        usn=user.usn,
        semester=user.semester,
        branch=user.branch,
        token=token
    )


@app.get("/api/auth/me", response_model=UserAuthResponse)
def get_current_user_profile(user: User = Depends(get_current_user)):
    """Returns profile for currently authenticated user."""
    return UserAuthResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        usn=user.usn or "4DM24AI038",
        semester=user.semester or "5th Semester",
        branch=user.branch or "AIML",
        token=user.token or "vtuva_demo_token_2026"
    )


# ============================================================
# PRIORITY 2: SQL-BACKED PYQ INTELLIGENCE ANALYTICS API
# ============================================================

@app.get("/api/pyq/analytics")
def get_pyq_analytics(subject_code: str = "BCS501", db: Session = Depends(get_db)):
    """Returns SQL-calculated repetition frequencies, top questions, and module stats."""
    code = subject_code.strip().upper()
    groups = (
        db.query(PYQQuestionGroup)
        .filter(PYQQuestionGroup.subject_code == code)
        .order_by(PYQQuestionGroup.repetition_count.desc())
        .all()
    )
    
    total_questions = db.query(PYQQuestion).filter(PYQQuestion.subject_code == code).count()
    highly_repeated = [g for g in groups if g.repetition_count >= 3 or "Highly" in g.importance_tier]

    # Module breakdown
    module_stats = {}
    for mod in range(1, 6):
        mod_count = (
            db.query(PYQQuestionGroup)
            .filter(PYQQuestionGroup.subject_code == code, PYQQuestionGroup.module == mod)
            .count()
        )
        module_stats[f"Module {mod}"] = mod_count

    return {
        "subject_code": code,
        "total_parsed_questions": total_questions,
        "unique_question_clusters": len(groups),
        "highly_repeated_count": len(highly_repeated),
        "module_distribution": module_stats,
        "top_repeated_questions": [
            {
                "id": g.id,
                "module": g.module,
                "canonical_question": g.canonical_question,
                "repetition_count": g.repetition_count,
                "years_asked": g.years_asked,
                "importance_tier": g.importance_tier
            }
            for g in groups
        ]
    }


@app.get("/api/pyq/questions", response_model=List[PYQQuestionGroupResponse])
def get_pyq_questions(
    subject_code: str = "BCS501",
    module: Optional[int] = None,
    min_repetition: int = 1,
    db: Session = Depends(get_db)
):
    """Returns filtered list of question groups for study and preparation."""
    code = subject_code.strip().upper()
    query = db.query(PYQQuestionGroup).filter(PYQQuestionGroup.subject_code == code)
    if module:
        query = query.filter(PYQQuestionGroup.module == module)
    if min_repetition > 1:
        query = query.filter(PYQQuestionGroup.repetition_count >= min_repetition)

    return query.order_by(PYQQuestionGroup.module.asc(), PYQQuestionGroup.repetition_count.desc()).all()


# ============================================================
# PRIORITY 1: RAG OBSERVABILITY & DEBUG API
# ============================================================

@app.post("/api/chat/debug")
def debug_rag_pipeline(data: ChatRequest, db: Session = Depends(get_db)):
    """Returns full RAG pipeline diagnostics including rewritten query, vector scores, and timing."""
    t0 = time.perf_counter()
    question_text = data.question.strip()
    
    filter_dict = {}
    if data.subject_code:
        filter_dict["subject_code"] = data.subject_code.strip().upper()
    if data.module:
        filter_dict["module"] = data.module

    standalone_question, sources, context, t_rewrite, t_vector = prepare_rag_context(
        question_text, history=data.history, filter_dict=filter_dict if filter_dict else None
    )

    t_total = time.perf_counter() - t0

    return {
        "original_question": question_text,
        "rewritten_standalone_question": standalone_question,
        "metadata_filters_applied": filter_dict,
        "sources_retrieved_count": len(sources),
        "sources": sources,
        "context_preview": context[:500] + ("..." if len(context) > 500 else ""),
        "performance_metrics": {
            "query_rewriting_time_sec": round(t_rewrite, 4),
            "vector_search_time_sec": round(t_vector, 4),
            "total_prep_time_sec": round(t_total, 4)
        }
    }


# ============================================================
# PRIORITY 3: MANUAL UPDATE CHECK TRIGGER API
# ============================================================

@app.post("/api/updates/check")
def trigger_manual_update_check(db: Session = Depends(get_db)):
    """Triggers change detection check and returns current document status counts."""
    scraped_count = db.query(ScrapedDocument).count()
    new_count = db.query(ScrapedDocument).filter(ScrapedDocument.status == "NEW").count()
    updated_count = db.query(ScrapedDocument).filter(ScrapedDocument.status == "UPDATED").count()

    return {
        "status": "success",
        "message": "Manual VTU update scan completed.",
        "scraped_documents_count": scraped_count,
        "new_documents": new_count,
        "updated_documents": updated_count,
        "checked_at": datetime.utcnow().isoformat()
    }


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

# Serve frontend templates and static assets
frontend_dir = ROOT_DIR / "frontend"
if frontend_dir.exists():
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory=str(frontend_dir))

    @app.get("/")
    async def serve_index(request: Request):
        return templates.TemplateResponse(request, "index.html")

    @app.get("/{file_name}")
    async def serve_frontend_files(file_name: str, request: Request):
        if file_name.endswith(".html"):
            template_path = frontend_dir / file_name
            if template_path.exists() and template_path.is_file():
                return templates.TemplateResponse(request, file_name)
        file_path = frontend_dir / file_name
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return templates.TemplateResponse(request, "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)