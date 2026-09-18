import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore

try:
    from backend.rag.embeddings import get_embeddings
except ImportError:
    from embeddings import get_embeddings

load_dotenv()


def get_vector_store():
    """Connect to Qdrant vector database and return QdrantVectorStore instance."""
    embeddings = get_embeddings()

    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    if not qdrant_url:
        print("⚠️ Warning: QDRANT_URL environment variable is not set.")

    client = QdrantClient(
        url=qdrant_url,
        api_key=qdrant_api_key
    )

    vector_store = QdrantVectorStore(
        client=client,
        collection_name="vtuva_documents",
        embedding=embeddings
    )

    return vector_store