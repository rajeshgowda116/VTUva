import time
import trace
import traceback
from datetime import datetime
from typing import Optional, List, Dict, Any

from backend.database import SessionLocal
from backend.models import ScrapeRun, ScrapedDocument
from backend.scraper.config import ScraperConfig, default_config
from backend.scraper.crawler import PlaywrightCrawler
from backend.scraper.change_detector import process_scraped_documents
from backend.scraper.processor import process_changed_documents


def run_scrape_and_ingest_pipeline(
    config: Optional[ScraperConfig] = None,
    seed_urls: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Complete end-to-end scraper and RAG update pipeline.
    
    1. Crawls public VTU website using Playwright.
    2. Stores raw scraped pages and PDFs into SQL database.
    3. Runs SHA-256 change detection against SQL source of truth.
    4. Identifies NEW and UPDATED content.
    5. Cleans content, extracts metadata, chunks, and updates vector store.
    6. Logs statistics and updates ScrapeRun SQL record.
    """
    cfg = config or default_config
    db = SessionLocal()
    
    # 1. Create ScrapeRun record
    scrape_run = ScrapeRun(
        started_at=datetime.utcnow(),
        status="RUNNING"
    )
    db.add(scrape_run)
    db.commit()
    db.refresh(scrape_run)

    print(f"\n==================================================")
    print(f"[SCRAPER] Starting crawl run ID {scrape_run.id}")
    print(f"==================================================")

    try:
        # 2. Run Playwright Crawler
        crawler = PlaywrightCrawler(config=cfg)
        import asyncio
        scraped_items = asyncio.run(crawler.crawl(seed_urls=seed_urls))

        pages_discovered = len(crawler.discovered_urls)
        pages_scraped = len(scraped_items)
        failed_count = len(crawler.failed_urls)

        print(f"[SCRAPER] Discovered: {pages_discovered} URLs")
        print(f"[SCRAPER] Scraped: {pages_scraped} documents/pages")

        # 3. SQL Change Detection & Raw Storage
        change_res = process_scraped_documents(
            db=db,
            scraped_items=scraped_items,
            mark_removed_missing=False
        )

        counts = change_res["counts"]
        new_docs = change_res["new_docs"]
        updated_docs = change_res["updated_docs"]
        unchanged_docs = change_res["unchanged_docs"]
        removed_docs = change_res["removed_docs"]

        print(f"[CHANGE] New: {counts['new']}")
        print(f"[CHANGE] Updated: {counts['updated']}")
        print(f"[CHANGE] Unchanged: {counts['unchanged']}")
        if counts['removed'] > 0:
            print(f"[CHANGE] Removed: {counts['removed']}")

        # 4. RAG Ingestion for Changed Documents ONLY
        changed_docs = new_docs + updated_docs
        rag_processed_count = 0

        if changed_docs:
            print(f"[RAG] Processing {len(changed_docs)} changed documents...")
            rag_processed_count = process_changed_documents(db, changed_docs)
            print(f"[RAG] Completed processing {rag_processed_count} documents into Vector DB.")
        else:
            print(f"[RAG] No changed documents to ingest. Vector DB remains unchanged.")

        # 5. Complete ScrapeRun statistics
        scrape_run.completed_at = datetime.utcnow()
        scrape_run.status = "COMPLETED"
        scrape_run.pages_discovered = pages_discovered
        scrape_run.pages_scraped = pages_scraped
        scrape_run.new_documents = counts["new"]
        scrape_run.updated_documents = counts["updated"]
        scrape_run.unchanged_documents = counts["unchanged"]
        scrape_run.removed_documents = counts["removed"]
        scrape_run.failed_documents = failed_count
        scrape_run.rag_documents_processed = rag_processed_count

        db.commit()
        print(f"[SCRAPER] Crawl run ID {scrape_run.id} completed successfully.")
        print(f"==================================================\n")

        return {
            "run_id": scrape_run.id,
            "status": "COMPLETED",
            "pages_discovered": pages_discovered,
            "pages_scraped": pages_scraped,
            "new_documents": counts["new"],
            "updated_documents": counts["updated"],
            "unchanged_documents": counts["unchanged"],
            "removed_documents": counts["removed"],
            "failed_documents": failed_count,
            "rag_documents_processed": rag_processed_count,
            "completed_at": scrape_run.completed_at.isoformat()
        }

    except Exception as e:
        err_msg = f"{e}\n{traceback.format_exc()}"
        print(f"[SCRAPER ERROR] Crawl run ID {scrape_run.id} failed: {e}")
        db.rollback()
        
        scrape_run.completed_at = datetime.utcnow()
        scrape_run.status = "FAILED"
        scrape_run.error_message = str(e)
        db.commit()
        
        return {
            "run_id": scrape_run.id,
            "status": "FAILED",
            "error_message": str(e),
            "completed_at": scrape_run.completed_at.isoformat()
        }
    finally:
        db.close()
