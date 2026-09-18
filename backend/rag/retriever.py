try:
    from backend.rag.vectordb import get_vector_store
except ImportError:
    from vectordb import get_vector_store


def get_retriever(k: int = 5):
    """Return retriever interface for Qdrant vector store."""
    vector_store = get_vector_store()

    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": k
        }
    )

    return retriever