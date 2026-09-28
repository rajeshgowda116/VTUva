import re
from urllib.parse import urlparse, urljoin, urlunparse, parse_qsl, urlencode
from typing import List, Set
from bs4 import BeautifulSoup
from backend.scraper.config import ScraperConfig, default_config


def normalize_url(url: str, base_url: str = None) -> str:
    """
    Normalizes a URL by joining with base_url if relative, stripping fragments,
    lowercasing scheme and domain, and sorting query params.
    """
    if not url or not url.strip():
        return ""
    
    url = url.strip()
    if base_url:
        url = urljoin(base_url, url)
        
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ""

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    
    # Strip default ports if included
    if ":" in netloc:
        host, port = netloc.split(":", 1)
        if (scheme == "http" and port == "80") or (scheme == "https" and port == "443"):
            netloc = host

    # Normalize path: collapse multiple slashes, remove trailing slash if path > 1 char
    path = parsed.path
    if path:
        path = re.sub(r"/{2,}", "/", path)
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]
    else:
        path = "/"

    # Sort query parameters for consistent canonical representation
    query = ""
    if parsed.query:
        query_tuples = parse_qsl(parsed.query, keep_blank_values=True)
        # Filter out common tracking / session params
        filtered_tuples = [
            (k, v) for k, v in query_tuples
            if k.lower() not in {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "phpsessid", "sid"}
        ]
        if filtered_tuples:
            filtered_tuples.sort(key=lambda x: x[0])
            query = urlencode(filtered_tuples)

    # Reconstruct without fragment
    normalized = urlunparse((scheme, netloc, path, parsed.params, query, ""))
    return normalized


def is_allowed_domain(url: str, allowed_domains: List[str]) -> bool:
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    for allowed in allowed_domains:
        if domain == allowed.lower() or domain.endswith("." + allowed.lower()):
            return True
    return False


def is_allowed_url(url: str, config: ScraperConfig = default_config) -> bool:
    if not url:
        return False
    
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False

    if not is_allowed_domain(url, config.allowed_domains):
        return False

    path = parsed.path.lower()
    
    # Check blocked paths
    for blocked in config.blocked_paths:
        if blocked.lower() in path:
            return False

    # Check blocked extensions
    for ext in config.blocked_file_extensions:
        if path.endswith(ext.lower()):
            return False

    # If file has an extension, check if allowed
    dot_pos = path.rfind(".")
    slash_pos = path.rfind("/")
    if dot_pos > slash_pos:
        ext = path[dot_pos:]
        if ext not in config.allowed_file_extensions:
            return False

    return True


def extract_links(html_content: str, base_url: str, config: ScraperConfig = default_config) -> Set[str]:
    """
    Extracts all valid internal hyperlinks from raw HTML content.
    """
    discovered: Set[str] = set()
    if not html_content:
        return discovered

    try:
        soup = BeautifulSoup(html_content, "html.parser")
    except Exception:
        return discovered

    tags_attrs = [
        ("a", "href"),
        ("iframe", "src"),
        ("embed", "src"),
        ("object", "data"),
    ]

    for tag, attr in tags_attrs:
        for element in soup.find_all(tag, href=True if attr == "href" else True):
            val = element.get(attr)
            if not val:
                continue
            
            val = val.strip()
            if val.startswith(("javascript:", "mailto:", "tel:", "data:", "#")):
                continue

            normalized = normalize_url(val, base_url=base_url)
            if normalized and is_allowed_url(normalized, config):
                discovered.add(normalized)

    return discovered
