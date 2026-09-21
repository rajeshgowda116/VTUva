from pathlib import Path
try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

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