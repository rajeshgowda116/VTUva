import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Set

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
SCRAPED_PDFS_DIR = DATA_DIR / "scraped_pdfs"


class ScraperConfig(BaseModel):
    seed_urls: List[str] = Field(
        default_factory=lambda: [
            os.getenv("VTU_SEED_URL", "https://vtu.ac.in/")
        ]
    )
    allowed_domains: List[str] = Field(
        default_factory=lambda: ["vtu.ac.in", "www.vtu.ac.in"]
    )
    allowed_path_prefixes: List[str] = Field(
        default_factory=lambda: ["/"]
    )
    blocked_paths: List[str] = Field(
        default_factory=lambda: [
            "/wp-admin", "/wp-login", "/login", "/cgi-bin",
            "/feed", "/cart", "/checkout", "/my-account"
        ]
    )
    allowed_file_extensions: Set[str] = Field(
        default_factory=lambda: {
            ".html", ".htm", ".php", ".aspx", ".jsp", ".asp", ".pdf", ".doc", ".docx", ".xls", ".xlsx"
        }
    )
    blocked_file_extensions: Set[str] = Field(
        default_factory=lambda: {
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".css", ".js",
            ".mp4", ".mp3", ".avi", ".mov", ".zip", ".rar", ".tar", ".gz",
            ".woff", ".woff2", ".ttf", ".eot"
        }
    )
    max_depth: int = int(os.getenv("SCRAPER_MAX_DEPTH", "2"))
    max_pages: int = int(os.getenv("SCRAPER_MAX_PAGES", "100"))
    concurrency_limit: int = int(os.getenv("SCRAPER_CONCURRENCY", "3"))
    request_timeout_ms: int = int(os.getenv("SCRAPER_TIMEOUT_MS", "30000"))
    request_delay_seconds: float = float(os.getenv("SCRAPER_DELAY_SEC", "1.0"))
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36 (VTUva Scraper Bot/1.0)"
    )
    pdf_save_dir: Path = SCRAPED_PDFS_DIR
    schedule_interval_hours: int = 12


default_config = ScraperConfig()
