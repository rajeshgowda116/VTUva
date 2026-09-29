from typing import Dict, Any, List
from bs4 import BeautifulSoup
from .url_discovery import extract_links, normalize_url


def parse_html_page(html_content: str, page_url: str) -> Dict[str, Any]:
    """
    Parses raw HTML content to extract page title, canonical URL, raw text, headings,
    and associated document (PDF, etc.) links.
    """
    result: Dict[str, Any] = {
        "title": "",
        "canonical_url": page_url,
        "raw_text": "",
        "headings": [],
        "pdf_links": [],
        "meta_description": "",
    }
    
    if not html_content or not html_content.strip():
        return result

    try:
        soup = BeautifulSoup(html_content, "html.parser")
    except Exception as e:
        print(f"[PageParser Error] Failed to parse HTML for {page_url}: {e}")
        return result

    # 1. Extract Page Title
    if soup.title and soup.title.string:
        result["title"] = soup.title.string.strip()
    elif soup.find("h1"):
        result["title"] = soup.find("h1").get_text(strip=True)

    # 2. Extract Canonical URL from <link rel="canonical">
    canonical_tag = soup.find("link", rel="canonical")
    if canonical_tag and canonical_tag.get("href"):
        norm_canonical = normalize_url(canonical_tag.get("href"), base_url=page_url)
        if norm_canonical:
            result["canonical_url"] = norm_canonical

    # 3. Meta Description
    meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if meta_desc and meta_desc.get("content"):
        result["meta_description"] = meta_desc.get("content").strip()

    # 4. Extract Headings (h1 - h6)
    headings = []
    for h_tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        text = h_tag.get_text(strip=True)
        if text:
            headings.append({"level": h_tag.name, "text": text})
    result["headings"] = headings

    # 5. Extract Document / PDF Links
    pdf_links = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if href.lower().endswith(".pdf") or ".pdf?" in href.lower():
            norm_pdf = normalize_url(href, base_url=page_url)
            if norm_pdf:
                pdf_links.add(norm_pdf)
    result["pdf_links"] = list(pdf_links)

    # 6. Extract Raw Body Text
    body = soup.find("body") or soup
    body_clone = BeautifulSoup(str(body), "html.parser")
    for script_or_style in body_clone(["script", "style", "noscript"]):
        script_or_style.decompose()

    result["raw_text"] = body_clone.get_text(separator="\n", strip=True)

    return result
