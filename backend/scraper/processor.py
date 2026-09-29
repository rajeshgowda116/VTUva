from typing import List, Dict, Any
from sqlalchemy.orm import Session
from langchain_core.documents import Document

try:
    from backend.database import SessionLocal
    from backend.models import ScrapedDocument
    from backend.rag.retriever import get_vector_store
    from backend.rag.splitter import split_documents
except ImportError:
    from database import SessionLocal
    from models import ScrapedDocument
    from rag.retriever import get_vector_store
    from rag.splitter import split_documents

from .cleaner import clean_html_content, clean_text_content
from .metadata import extract_metadata


def process_changed_documents(db: Session, changed_docs: List[ScrapedDocument]) -> int:
    """
    Cleans, extracts metadata, chunks, and ingests changed (NEW and UPDATED) documents
    into the existing VTUva ChromaDB vector store.
    """
    if not changed_docs:
        print("[RAG Processor] No changed documents to process.")
        return 0

    vector_store = get_vector_store()
    total_processed = 0

    for doc in changed_docs:
        print(f"[RAG Processor] Processing doc ID {doc.id} ({doc.status}, v{doc.version}): {doc.url}")
        doc.processing_status = "PROCESSING"
        db.commit()

        try:
            # 1. Clean raw content
            if doc.content_type == "html":
                cleaned_text = clean_html_content(doc.content or "")
            else:
                cleaned_text = clean_text_content(doc.content or "")

            if not cleaned_text or not cleaned_text.strip():
                print(f"[RAG Processor Warning] Empty text after cleaning for {doc.url}, skipping chunking.")
                doc.processing_status = "PROCESSED"
                db.commit()
                continue

            # 2. Extract Metadata
            meta = extract_metadata(
                url=doc.url,
                title=doc.title or "",
                content_text=cleaned_text,
                content_type=doc.content_type or "html",
                content_hash=doc.content_hash,
                scraped_at=doc.last_scraped_at
            )

            # 3. Chunk cleaned content
            raw_doc_items = [{"text": cleaned_text, "page": 1, "source": doc.url}]
            chunks = split_documents(raw_doc_items)

            if not chunks:
                doc.processing_status = "PROCESSED"
                db.commit()
                continue

            # 4. If UPDATED document: purge old vector records for this document
            if doc.status == "UPDATED":
                try:
                    if hasattr(vector_store, "_collection") and vector_store._collection:
                        vector_store._collection.delete(where={"url": doc.url})
                        print(f"   [VectorDB] Purged previous vector chunks for URL: {doc.url}")
                except Exception as del_err:
                    print(f"   [VectorDB Warning] Could not purge old chunks for {doc.url}: {del_err}")

            # 5. Build LangChain documents with metadata
            langchain_docs = []
            for idx, chunk in enumerate(chunks):
                chunk_meta = {
                    "source": doc.url,
                    "url": doc.url,
                    "doc_id": doc.id,
                    "version": doc.version,
                    "title": doc.title or "VTU Page",
                    "content_hash": doc.content_hash,
                    "content_type": doc.content_type or "html",
                    "document_type": meta.get("document_type", "general"),
                    "subject_code": meta.get("subject_code", ""),
                    "scheme": meta.get("scheme", ""),
                    "branch": meta.get("branch", ""),
                    "page": chunk.get("page", 1),
                    "chunk_index": idx
                }
                langchain_docs.append(
                    Document(page_content=chunk["text"], metadata=chunk_meta)
                )

            # 6. Add new document chunks to ChromaDB
            vector_store.add_documents(langchain_docs)
            print(f"   [VectorDB] Added {len(langchain_docs)} chunks for {doc.url}")

            doc.processing_status = "PROCESSED"
            total_processed += 1

        except Exception as e:
            print(f"[RAG Processor Error] Failed processing document {doc.id} ({doc.url}): {e}")
            doc.processing_status = "FAILED"

        db.commit()

    print(f"[RAG Processor] Successfully ingested/updated {total_processed} changed documents into Vector Database.")
    return total_processed
