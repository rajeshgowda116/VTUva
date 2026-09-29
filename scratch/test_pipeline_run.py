import sys
import asyncio
from pathlib import Path

# Fix Windows console encoding for logging outputs
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.scraper.config import ScraperConfig
from backend.scraper.pipeline import run_scrape_and_ingest_pipeline

def main():
    config = ScraperConfig(
        seed_urls=["https://vtu.ac.in/"],
        max_depth=1,
        max_pages=3,
        concurrency_limit=2,
        request_timeout_ms=30000,
        request_delay_seconds=0.5
    )
    
    print("Testing run_scrape_and_ingest_pipeline on VTU site...")
    result = run_scrape_and_ingest_pipeline(config=config)
    print("\n--- PIPELINE RESULT ---")
    print(result)

if __name__ == "__main__":
    main()
