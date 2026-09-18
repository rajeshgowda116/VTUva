from pathlib import Path
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

try:
    from backend.rag.cleaner import clean_text
except ImportError:
    from cleaner import clean_text


def load_pdfs(folder_path) -> List[Document]:
    """Load all PDF documents from folder_path, clean text, and return a list of Document objects."""
    folder = Path(folder_path)

    if not folder.exists():
        print("❌ Folder not found:", folder)
        return []

    pdf_files = list(folder.rglob("*.pdf"))

    if not pdf_files:
        print("⚠️ No PDF files found in:", folder)
        return []

    documents: List[Document] = []
    total_pages = 0
    skipped_pages = 0

    for pdf_file in pdf_files:
        print(f"📄 Loading PDF: {pdf_file.name}")
        try:
            loader = PyPDFLoader(str(pdf_file))
            file_docs = loader.load()

            for doc in file_docs:
                cleaned = clean_text(doc.page_content)
                if not cleaned:
                    skipped_pages += 1
                    continue

                doc.page_content = cleaned
                doc.metadata["file_name"] = pdf_file.name
                doc.metadata["source"] = str(pdf_file)
                documents.append(doc)
                total_pages += 1

        except Exception as e:
            print(f"❌ Error reading {pdf_file.name}: {e}")

    print("======================")
    print(f"Pages successfully loaded: {total_pages}")
    print(f"Blank/empty pages skipped: {skipped_pages}")
    print("======================")

    return documents


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    pdf_folder = project_root / "data" / "frist_sem"

    docs = load_pdfs(pdf_folder)
    print(f"Total document pages retrieved: {len(docs)}")