import os
import hashlib
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
import urllib.request
import urllib.error
from pypdf import PdfReader
from backend.scraper.config import ScraperConfig, default_config


def compute_bytes_hash(content_bytes: bytes) -> str:
    return hashlib.sha256(content_bytes).hexdigest()


async def download_and_parse_pdf(
    pdf_url: str,
    parent_url: Optional[str] = None,
    config: ScraperConfig = default_config
) -> Dict[str, Any]:
    """
    Downloads a public PDF file asynchronously, saves it to the configured
    pdf_save_dir, extracts raw text using pypdf, and computes its SHA-256 hash.
    """
    config.pdf_save_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename based on URL hash to prevent collisions
    url_hash = hashlib.md5(pdf_url.encode("utf-8")).hexdigest()[:10]
    raw_filename = pdf_url.split("/")[-1].split("?")[0]
    if not raw_filename.endswith(".pdf"):
        raw_filename = f"{raw_filename}.pdf"
    
    safe_filename = f"{url_hash}_{raw_filename}"
    file_path = config.pdf_save_dir / safe_filename

    result: Dict[str, Any] = {
        "url": pdf_url,
        "canonical_url": pdf_url,
        "title": raw_filename.replace("_", " ").replace(".pdf", ""),
        "file_path": str(file_path),
        "mime_type": "application/pdf",
        "content_type": "pdf",
        "source_type": "pdf_document",
        "parent_url": parent_url,
        "raw_text": "",
        "content_hash": "",
        "num_pages": 0,
        "error": None,
    }

    try:
        # Download file using asyncio thread runner to prevent blocking loop
        def _download():
            req = urllib.request.Request(
                pdf_url,
                headers={"User-Agent": config.user_agent}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()

        pdf_bytes = await asyncio.to_thread(_download)
        
        # Save raw binary content to disk
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        # Compute content hash on raw PDF bytes
        result["content_hash"] = compute_bytes_hash(pdf_bytes)

        # Extract text using pypdf
        def _extract_pdf_text():
            reader = PdfReader(file_path)
            extracted_pages = []
            for i, page in enumerate(reader.pages):
                txt = page.extract_text()
                if txt and txt.strip():
                    extracted_pages.append(f"--- Page {i+1} ---\n{txt.strip()}")
            return len(reader.pages), "\n\n".join(extracted_pages)

        num_pages, raw_text = await asyncio.to_thread(_extract_pdf_text)
        result["num_pages"] = num_pages
        result["raw_text"] = raw_text

        print(f"[PDF Handler] Successfully downloaded & extracted PDF ({num_pages} pages): {safe_filename}")

    except Exception as e:
        error_msg = f"Failed to download/parse PDF ({pdf_url}): {e}"
        print(f"[PDF Handler Error] {error_msg}")
        result["error"] = error_msg

    return result
