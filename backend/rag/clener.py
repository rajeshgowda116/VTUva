import re


def clean_text(text):
    # Remove extra spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Remove too many blank lines
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    # Remove spaces at the beginning and end of lines
    text = "\n".join(line.strip() for line in text.splitlines())

    # Remove leading/trailing whitespace
    text = text.strip()

    return text