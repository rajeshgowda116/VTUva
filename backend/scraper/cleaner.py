import re
import html
from bs4 import BeautifulSoup


def clean_html_content(raw_html: str) -> str:
    """
    Cleans raw HTML by stripping boilerplate elements (nav, footer, header, script, style, ads, cookie banners)
    and normalizing headings, whitespace, and structural text.
    Uses robust container validation to prevent accidental selection of small empty sub-elements.
    """
    if not raw_html or not raw_html.strip():
        return ""

    try:
        soup = BeautifulSoup(raw_html, "html.parser")
    except Exception:
        return raw_html

    # Remove irrelevant non-content elements
    unwanted_selectors = [
        "script", "style", "noscript", "iframe", "svg", "button",
        "header", "footer", "nav", ".nav", ".navbar", ".navigation",
        "#header", "#footer", "#nav", "#navigation", "#menu", ".menu",
        "#primary-menu", ".sidebar", "#sidebar", ".cookie-banner", ".cookie-consent",
        ".advertisement", ".ads", ".banner", ".social-share", ".popup", ".widget-area"
    ]
    
    for selector in unwanted_selectors:
        for element in soup.select(selector):
            element.decompose()

    body = soup.find("body") or soup

    # Priority list of content container candidates
    candidates = [
        soup.find("main"),
        soup.find(id=re.compile(r"\b(main-content|home-main-content|primary|content)\b", re.I)),
        soup.find(class_=re.compile(r"\b(entry-content|main-content|site-content|page-content|content-area)\b", re.I)),
        soup.find("article")
    ]

    selected_content = None
    for cand in candidates:
        if cand:
            txt = cand.get_text(separator="\n", strip=True)
            if len(txt) >= 100:
                selected_content = cand
                break

    if not selected_content:
        selected_content = body

    text = selected_content.get_text(separator="\n", strip=True)
    return clean_text_content(text)


def clean_text_content(text: str) -> str:
    """
    Normalizes raw text content: handles HTML entity unescaping, converts non-breaking spaces
    and zero-width spaces, removes duplicate adjacent lines, and strips noise.
    """
    if not text:
        return ""

    # Unescape HTML entities (&amp;, &nbsp;, &quot;, &#8217;, etc.)
    text = html.unescape(text)

    # Replace windows line endings, non-breaking spaces, and zero-width spaces
    text = text.replace("\r\n", "\n").replace("\xa0", " ").replace("\u200b", "").replace("\r", "\n")

    lines = []
    last_line = None

    for line in text.split("\n"):
        line_str = re.sub(r"[ \t]+", " ", line).strip()
        if line_str and not line_str.startswith(("<!--", "-->")):
            # Prevent endless consecutive identical line repetition
            if line_str != last_line:
                lines.append(line_str)
                last_line = line_str

    cleaned = "\n".join(lines)
    return cleaned

