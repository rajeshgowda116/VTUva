import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.scraper.crawler import PlaywrightCrawler
from backend.scraper.config import ScraperConfig

async def main():
    config = ScraperConfig(
        seed_urls=["https://vtu.ac.in/"],
        max_depth=2,
        max_pages=10,
        concurrency_limit=2,
        request_timeout_ms=30000,
        request_delay_seconds=0.5
    )
    
    crawler = PlaywrightCrawler(config=config)
    documents = await crawler.crawl()
    
    print("\n--- CRAWL SUMMARY ---")
    print(f"Discovered URLs count: {len(crawler.discovered_urls)}")
    print(f"Scraped Documents count: {len(crawler.scraped_documents)}")
    print(f"Failed URLs count: {len(crawler.failed_urls)}")
    
    print("\n--- SAMPLE SCRAPED DOCUMENTS ---")
    for idx, doc in enumerate(documents[:5]):
        print(f"\nDocument #{idx+1}:")
        print(f"  URL: {doc.get('url')}")
        print(f"  Title: {doc.get('title')}")
        print(f"  Type: {doc.get('content_type')}")
        print(f"  Mime: {doc.get('mime_type')}")
        print(f"  PDF Links Found: {len(doc.get('pdf_links', []))}")
        raw_text = doc.get("raw_text", "")
        print(f"  Raw Text Length: {len(raw_text)}")
        print(f"  Raw Text Snippet: {raw_text[:200]!r}")

    if crawler.failed_urls:
        print("\n--- FAILED URLS ---")
        for f in crawler.failed_urls:
            print(f"  Failed URL: {f.get('url')} | Error: {f.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())
