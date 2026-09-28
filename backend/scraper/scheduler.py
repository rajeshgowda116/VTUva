import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from backend.scraper.config import default_config
from backend.scraper.pipeline import run_scrape_and_ingest_pipeline

_scheduler_task: Optional[asyncio.Task] = None
_is_running_pipeline: bool = False
_last_run_time: Optional[datetime] = None
_next_run_time: Optional[datetime] = None
_last_run_result: Optional[Dict[str, Any]] = None


def _execute_pipeline_task():
    global _is_running_pipeline, _last_run_time, _last_run_result
    if _is_running_pipeline:
        print("[SCHEDULER] Pipeline is already running. Skipping concurrent trigger.")
        return

    _is_running_pipeline = True
    try:
        print(f"\n[SCHEDULER] Triggering scheduled scrape pipeline at {datetime.utcnow().isoformat()}...")
        res = run_scrape_and_ingest_pipeline()
        _last_run_result = res
        _last_run_time = datetime.utcnow()
    except Exception as e:
        print(f"[SCHEDULER ERROR] Pipeline run failed: {e}")
        _last_run_result = {"status": "FAILED", "error": str(e)}
    finally:
        _is_running_pipeline = False


async def _scheduler_loop():
    global _next_run_time
    interval_seconds = default_config.schedule_interval_hours * 3600
    
    print(f"[SCHEDULER] Starting automated VTU scraper scheduler (Interval: {default_config.schedule_interval_hours} hours).")

    while True:
        _next_run_time = datetime.utcnow() + timedelta(seconds=interval_seconds)
        
        # Sleep until next scheduled run
        await asyncio.sleep(interval_seconds)
        
        # Run pipeline in a background thread to keep event loop responsive
        await asyncio.to_thread(_execute_pipeline_task)


def start_scraper_scheduler():
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        loop = asyncio.get_event_loop()
        _scheduler_task = loop.create_task(_scheduler_loop())
        print("[SCHEDULER] Background scheduler task started.")


def stop_scraper_scheduler():
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        _scheduler_task = None
        print("[SCHEDULER] Background scheduler task stopped.")


def trigger_scrape_now() -> bool:
    """
    Triggers an immediate scrape pipeline execution in a background thread.
    Returns True if started, False if already running.
    """
    global _is_running_pipeline
    if _is_running_pipeline:
        return False

    thread = threading.Thread(target=_execute_pipeline_task, daemon=True)
    thread.start()
    return True


def get_scheduler_status() -> Dict[str, Any]:
    global _scheduler_task, _is_running_pipeline, _last_run_time, _next_run_time, _last_run_result
    return {
        "scheduler_active": _scheduler_task is not None and not _scheduler_task.done(),
        "is_running_pipeline": _is_running_pipeline,
        "interval_hours": default_config.schedule_interval_hours,
        "last_run_time": _last_run_time.isoformat() if _last_run_time else None,
        "next_run_time": _next_run_time.isoformat() if _next_run_time else None,
        "last_run_result": _last_run_result
    }
