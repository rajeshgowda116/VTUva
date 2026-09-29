import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.scraper.config import ScraperConfig
from backend.scraper.pipeline import run_scrape_and_ingest_pipeline
from backend.rag.pipeline import ask_question

def main():
    print("Scraping & Ingesting VTU circulars and recent updates...")
    config = ScraperConfig(
        seed_urls=[
            "https://vtu.ac.in/",
            "https://vtu.ac.in/ict-circular-notification/",
            "https://vtu.ac.in/en/category/tenders/"
        ],
        max_depth=2,
        max_pages=15,
        concurrency_limit=3,
        request_timeout_ms=30000,
        request_delay_seconds=0.5
    )
    
    result = run_scrape_and_ingest_pipeline(config=config)
    print("\nCrawl Result:", result)

    print("\n--- TESTING RAG QUERY AGAIN ---")
    query = "What are the recent VTU circulars and notifications?"
    rag_res = ask_question(query)
    print("Question:", query)
    print("Answer:\n", rag_res.get("answer"))
    print("\nSources:")
    for s in rag_res.get("sources", []):
        print(f" - {s.get('file_name')} (Page {s.get('page')})")

if __name__ == "__main__":
    main()
