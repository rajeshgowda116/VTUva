from pypdf import PdfReader
from pathlib import Path


def lazy_load_pdf(file_path):

    pdf_file = Path(file_path)

    print(f"Reading: {pdf_file}")

    reader = PdfReader(pdf_file)

    for page_number, page in enumerate(reader.pages):

        text = page.extract_text()

        # Skip blank/image-only pages
        if text and text.strip():

            yield {
                "text": text,
                "page": page_number + 1,
                "source": str(pdf_file)
            }