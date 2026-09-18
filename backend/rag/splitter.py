from typing import List, Union, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def split_documents(documents: List[Union[Document, Dict[str, Any]]], chunk_size: int = 1000, chunk_overlap: int = 150) -> List[Document]:
    """Split documents or document dicts into smaller text chunks for vector embedding."""
    if not documents:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    # Check if documents is a list of LangChain Document objects or dicts
    if isinstance(documents[0], Document):
        chunks = splitter.split_documents(documents)
    else:
        chunks = splitter.create_documents(
            [doc["text"] for doc in documents],
            metadatas=[doc.get("metadata", {}) for doc in documents]
        )

    print(f"✂️ Split {len(documents)} document pages into {len(chunks)} text chunks.")
    return chunks
