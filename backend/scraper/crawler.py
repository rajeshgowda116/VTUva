import asyncio
import time
from typing import List, Dict, Any, Set, Optional
from playwright.async_api import async_playwright, Browser, Page

from backend.scraper.config import ScraperConfig, default_config
from backend.scraper.url_discovery import normalize_url, is_allowed_url, extract_links
from backend.scraper.page_parser import parse_html_page
from backend.scraper.pdf_handler import download_and_parse_pdf


class PlaywrightCrawler:
    """
    Asynchronous Playwright crawler for rendering JavaScript, discovering URLs,
    extracting HTML raw content, and collecting downloadable documents/PDFs.
    """

    def __init__(self, config: ScraperConfig = default_config):
        self.config = config
        self.visited_urls: Set[str] = set()
        self.scraped_documents: List[Dict[str, Any]] = []
        self.failed_urls: List[Dict[str, Any]] = []
        self.discovered_urls: Set[str] = set()

    async def crawl(self, seed_urls: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Executes controlled crawl starting from seed_urls.
        Returns a list of dictionary records containing raw page data and downloaded PDFs.
        """
        seeds = seed_urls or self.config.seed_urls
        queue: List[Dict[str, Any]] = []

        for seed in seeds:
            norm_seed = normalize_url(seed)
            if norm_seed and is_allowed_url(norm_seed, self.config):
                queue.append({"url": norm_seed, "depth": 0, "parent_url": None})
                self.discovered_urls.add(norm_seed)

        print(f"\n[SCRAPER] Starting crawl with {len(queue)} seed URLs (Max Depth={self.config.max_depth}, Max Pages={self.config.max_pages})")

        semaphore = asyncio.Semaphore(self.config.concurrency_limit)

        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                user_agent=self.config.user_agent,
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True
            )

            try:
                while queue and len(self.scraped_documents) < self.config.max_pages:
                    # Take batch up to concurrency_limit
                    batch = []
                    while queue and len(batch) < self.config.concurrency_limit:
                        item = queue.pop(0)
                        if item["url"] not in self.visited_urls:
                            self.visited_urls.add(item["url"])
                            batch.append(item)

                    if not batch:
                        break

                    tasks = [
                        self._crawl_item(context, item, queue, semaphore)
                        for item in batch
                    ]
                    await asyncio.gather(*tasks, return_exceptions=True)

            finally:
                await context.close()
                await browser.close()

        print(f"[SCRAPER] Crawl complete. Discovered: {len(self.discovered_urls)}, Scraped: {len(self.scraped_documents)}, Failed: {len(self.failed_urls)}")
        return self.scraped_documents

    async def _crawl_item(
        self,
        context,
        item: Dict[str, Any],
        queue: List[Dict[str, Any]],
        semaphore: asyncio.Semaphore
    ):
        async with semaphore:
            url = item["url"]
            depth = item["depth"]
            parent_url = item["parent_url"]

            # Check if target is direct PDF
            if url.lower().endswith(".pdf") or ".pdf?" in url.lower():
                print(f"[SCRAPER] Found PDF URL at depth {depth}: {url}")
                pdf_res = await download_and_parse_pdf(url, parent_url=parent_url, config=self.config)
                if not pdf_res.get("error"):
                    pdf_res["depth"] = depth
                    self.scraped_documents.append(pdf_res)
                else:
                    self.failed_urls.append({"url": url, "error": pdf_res["error"], "depth": depth})
                return

            # HTML Page Crawl using Playwright page
            print(f"[SCRAPER] Crawling HTML page [Depth {depth}]: {url}")
            page: Page = await context.new_page()
            try:
                # Set default timeouts
                page.set_default_timeout(self.config.request_timeout_ms)

                # Polite delay before request
                if self.config.request_delay_seconds > 0:
                    await asyncio.sleep(self.config.request_delay_seconds)

                response = await page.goto(url, wait_until="domcontentloaded")
                status = response.status if response else 0
                headers = response.headers if response else {}

                if response and status >= 400:
                    err_msg = f"HTTP status {status}"
                    print(f"[SCRAPER Warning] Failed URL {url}: {err_msg}")
                    self.failed_urls.append({"url": url, "error": err_msg, "depth": depth})
                    await page.close()
                    return

                content_type = headers.get("content-type", "text/html")
                raw_html = await page.content()
                
                # Parse page HTML structure & metadata
                parsed = parse_html_page(raw_html, page_url=url)
                
                doc_record = {
                    "url": url,
                    "canonical_url": parsed["canonical_url"],
                    "title": parsed["title"] or url,
                    "content": raw_html,  # Keep original raw HTML separately as required
                    "raw_text": parsed["raw_text"],
                    "content_type": "html",
                    "mime_type": content_type.split(";")[0],
                    "source_type": "web_page",
                    "parent_url": parent_url,
                    "depth": depth,
                    "etag": headers.get("etag", ""),
                    "last_modified": headers.get("last-modified", ""),
                    "pdf_links": parsed["pdf_links"],
                }
                self.scraped_documents.append(doc_record)

                # Discover new links if within depth limit
                if depth < self.config.max_depth:
                    new_links = extract_links(raw_html, base_url=url, config=self.config)
                    # Also include PDF links discovered by parser
                    new_links.update(parsed["pdf_links"])

                    for link in new_links:
                        if link not in self.discovered_urls:
                            self.discovered_urls.add(link)
                            queue.append({"url": link, "depth": depth + 1, "parent_url": url})

            except Exception as e:
                err_str = str(e)
                print(f"[SCRAPER Error] Error crawling {url}: {err_str}")
                self.failed_urls.append({"url": url, "error": err_str, "depth": depth})
            finally:
                if not page.is_closed():
                    await page.close()
