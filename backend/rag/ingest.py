import os
from pathlib import Path
from dotenv import load_dotenv

try:
    from backend.rag.loader import load_pdfs
    from backend.rag.splitter import split_documents
    from backend.rag.vectordb import get_vector_store
except ImportError:
    from loader import load_pdfs
    from splitter import split_documents
    from vectordb import get_vector_store

load_dotenv()


def run_ingestion(data_folder: str = None):
    """Run document ingestion pipeline to store PDF chunks into Qdrant vector database."""
    if data_folder is None:
        project_root = Path(__file__).resolve().parents[2]
        data_folder = project_root / "data" / "frist_sem"

    print(f"🚀 Starting document ingestion from: {data_folder}")

    # 1. Load PDFs
    documents = load_pdfs(data_folder)
    if not documents:
        print("❌ Ingestion aborted: No valid documents loaded.")
        return

    # 2. Split documents into chunks
    chunks = split_documents(documents)
    if not chunks:
        print("❌ Ingestion aborted: No chunks produced.")
        return

    # 3. Store chunks into Qdrant
    print("⏳ Connecting to Qdrant vector store and indexing chunks...")
    vector_store = get_vector_store()
    vector_store.add_documents(chunks)

    print(f"✅ Successfully ingested {len(chunks)} chunks into Qdrant vector database collection!")


if __name__ == "__main__":
    run_ingestion()
