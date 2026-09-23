from pathlib import Path

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

try:
    import chromadb
except ImportError:
    chromadb = None

try:
    from .embeddings import get_embeddings
except ImportError:
    from embeddings import get_embeddings

CHROMA_PATH = Path(__file__).parent / "chroma_db"

_vector_store_instance = None
_retriever_instance = None


def get_vector_store():
    global _vector_store_instance
    if _vector_store_instance is None:
        embeddings = get_embeddings()
        try:
            if chromadb:
                client = chromadb.PersistentClient(path=str(CHROMA_PATH))
                _vector_store_instance = Chroma(
                    client=client,
                    collection_name="vtuva_documents",
                    embedding_function=embeddings
                )
            else:
                _vector_store_instance = Chroma(
                    persist_directory=str(CHROMA_PATH),
                    collection_name="vtuva_documents",
                    embedding_function=embeddings
                )
        except Exception as e:
            print(f"[Chroma Client Info] Initializing persistent vector store fallback: {e}")
            _vector_store_instance = Chroma(
                persist_directory=str(CHROMA_PATH),
                collection_name="vtuva_documents",
                embedding_function=embeddings
            )

        print(f"[INIT] Chroma Vector Store loaded with {_vector_store_instance._collection.count()} documents.")
    return _vector_store_instance


def get_retriever(k: int = 4):
    global _retriever_instance
    if _retriever_instance is None or _retriever_instance.search_kwargs.get("k") != k:
        vector_store = get_vector_store()
        _retriever_instance = vector_store.as_retriever(
            search_kwargs={"k": k}
        )
    return _retriever_instance