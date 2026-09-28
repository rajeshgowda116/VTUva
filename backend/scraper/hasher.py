import hashlib
from typing import Union


def compute_content_hash(content: Union[str, bytes]) -> str:
    """
    Computes a deterministic SHA-256 hash for raw string content or bytes.
    """
    if isinstance(content, str):
        # Normalize newline character sequences before hashing string content
        normalized_str = content.replace("\r\n", "\n").strip()
        return hashlib.sha256(normalized_str.encode("utf-8")).hexdigest()
    elif isinstance(content, bytes):
        return hashlib.sha256(content).hexdigest()
    else:
        return ""
