import re


def clean_text(text: str) -> str:
    """Clean text by stripping extra spaces and normalizing blank lines."""
    if not text:
        return ""

    # Remove extra horizontal spaces/tabs
    text = re.sub(r"[ \t]+", " ", text)

    # Remove repeated blank lines
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    # Remove leading/trailing whitespace on each line
    text = "\n".join(line.strip() for line in text.splitlines())

    # Final strip
    return text.strip()
