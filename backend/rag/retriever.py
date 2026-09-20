from pathlib import Path
from langchain_chroma import Chroma

try:
    from .embeddings import get_embeddings
except ImportError:
    from embeddings import get_embeddings

CHROMA_PATH = Path(__file__).parent / "chroma_db"


def get_retriever():
    embeddings = get_embeddings()

    vector_store = Chroma(
        persist_directory=str(CHROMA_PATH),
        collection_name="vtuva_documents",
        embedding_function=embeddings
    )

    print("Chroma documents count:", vector_store._collection.count())

    return vector_store.as_retriever(
        search_kwargs={"k": 15}
    )