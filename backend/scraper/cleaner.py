import re
from bs4 import BeautifulSoup


def clean_html_content(raw_html: str) -> str:
    """
    Cleans raw HTML by stripping boilerplate elements (nav, footer, header, script, style, ads, cookie banners)
    and normalizing headings, whitespace, and structural text.
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
        ".sidebar", "#sidebar", ".cookie-banner", ".cookie-consent",
        ".advertisement", ".ads", ".banner", ".social-share", ".popup"
    ]
    
    for selector in unwanted_selectors:
        for element in soup.select(selector):
            element.decompose()

    main_content = (
        soup.find("main") or
        soup.find("article") or
        soup.find(class_=re.compile(r"\b(entry-content|main-content|site-content|page-content|content-area)\b", re.I)) or
        soup.find(id=re.compile(r"\b(primary|main-content|content|main)\b", re.I)) or
        soup.find("body") or
        soup
    )

    # Extract text with newline separators
    text = main_content.get_text(separator="\n", strip=True)
    return clean_text_content(text)


def clean_text_content(text: str) -> str:
    """
    Normalizes raw text content: removes multiple blank lines, unifies line breaks,
    and strips noise.
    """
    if not text:
        return ""

    # Replace windows line endings
    text = text.replace("\r\n", "\n")

    # Collapse multiple spaces on the same line
    lines = []
    for line in text.split("\n"):
        line_str = re.sub(r"[ \t]+", " ", line).strip()
        if line_str:
            lines.append(line_str)

    # Rejoin with single newlines
    cleaned = "\n".join(lines)
    return cleaned
