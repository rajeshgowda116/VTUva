from langchain_core.documents import Document

try:
    from .retriever import get_vector_store
except ImportError:
    from retriever import get_vector_store


def add_documents(chunks):
    vector_store = get_vector_store()
    documents = []

    for chunk in chunks:
        documents.append(
            Document(
                page_content=chunk["text"],
                metadata={
                    "page": chunk["page"],
                    "source": chunk["source"]
                }
            )
        )

    vector_store.add_documents(documents)
    print(f"   Added {len(documents)} chunks to ChromaDB")