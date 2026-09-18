from langchain_chroma import Chroma
from langchain_core.documents import Document

from embeddings import get_embeddings


CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "vtuva_documents"


def get_vector_store():

    embeddings = get_embeddings()

    return Chroma(
        persist_directory=CHROMA_PATH,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings
    )


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