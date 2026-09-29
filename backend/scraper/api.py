import os
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

try:
    from backend.database import get_db
    from backend.models import ScrapeRun, ScrapedDocument
except ImportError:
    from database import get_db
    from models import ScrapeRun, ScrapedDocument

from .scheduler import get_scheduler_status, trigger_scrape_now

router = APIRouter(prefix="/api/admin/scraper", tags=["Admin Scraper"])

ADMIN_SECRET_KEY = os.getenv("ADMIN_API_KEY", None)


def verify_admin_access(x_admin_key: str = Header(None)):
    """
    Verifies admin access key if ADMIN_API_KEY environment variable is configured.
    """
    if ADMIN_SECRET_KEY and x_admin_key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized admin access.")


@router.get("/status")
def get_scraper_status(db: Session = Depends(get_db), _: None = Depends(verify_admin_access)):
    """
    Returns scraper background status, scheduler interval, last run time, next run time,
    and database statistics.
    """
    scheduler_info = get_scheduler_status()
    
    total_scraped_docs = db.query(ScrapedDocument).count()
    active_docs = db.query(ScrapedDocument).filter(ScrapedDocument.is_active == True).count()
    processed_docs = db.query(ScrapedDocument).filter(ScrapedDocument.processing_status == "PROCESSED").count()
    last_run = db.query(ScrapeRun).order_by(ScrapeRun.id.desc()).first()

    return {
        "status": "online",
        "scheduler": scheduler_info,
        "database_stats": {
            "total_documents": total_scraped_docs,
            "active_documents": active_docs,
            "processed_rag_documents": processed_docs,
        },
        "last_run": {
            "id": last_run.id if last_run else None,
            "status": last_run.status if last_run else None,
            "started_at": last_run.started_at.isoformat() if last_run and last_run.started_at else None,
            "completed_at": last_run.completed_at.isoformat() if last_run and last_run.completed_at else None,
            "pages_scraped": last_run.pages_scraped if last_run else 0,
            "new_documents": last_run.new_documents if last_run else 0,
            "updated_documents": last_run.updated_documents if last_run else 0,
            "unchanged_documents": last_run.unchanged_documents if last_run else 0,
            "rag_processed": last_run.rag_documents_processed if last_run else 0,
            "error_message": last_run.error_message if last_run else None,
        }
    }


@router.get("/runs")
def get_scraper_runs(limit: int = 20, db: Session = Depends(get_db), _: None = Depends(verify_admin_access)):
    """
    Returns history of recent scraping runs.
    """
    runs = db.query(ScrapeRun).order_by(ScrapeRun.id.desc()).limit(limit).all()
    return [
        {
            "id": run.id,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "status": run.status,
            "pages_discovered": run.pages_discovered,
            "pages_scraped": run.pages_scraped,
            "new_documents": run.new_documents,
            "updated_documents": run.updated_documents,
            "unchanged_documents": run.unchanged_documents,
            "removed_documents": run.removed_documents,
            "failed_documents": run.failed_documents,
            "rag_documents_processed": run.rag_documents_processed,
            "error_message": run.error_message,
        }
        for run in runs
    ]


@router.post("/run")
def trigger_scraper_run(_: None = Depends(verify_admin_access)):
    """
    Triggers an immediate automated scraping and RAG ingestion pipeline run in the background.
    """
    started = trigger_scrape_now()
    if not started:
        raise HTTPException(
            status_code=409,
            detail="Scraper pipeline is already running in the background."
        )
    return {
        "message": "Scraper pipeline execution triggered successfully in background.",
        "timestamp": datetime.utcnow().isoformat()
    }
