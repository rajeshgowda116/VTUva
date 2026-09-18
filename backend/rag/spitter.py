try:
    from backend.rag.splitter import split_documents
except ImportError:
    from splitter import split_documents

__all__ = ["split_documents"]