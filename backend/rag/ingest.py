import hashlib
import json
from pathlib import Path

from loader import load_pdf
from splitter import split_documents
from vectordb import add_documents


DATA_PATH = Path("../../data")
PROCESSED_FILE = Path("processed_files.json")


def calculate_hash(file_path):

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:

        while chunk := f.read(8192):
            sha256.update(chunk)

    return sha256.hexdigest()


def load_processed_files():

    if not PROCESSED_FILE.exists():
        return {}

    try:
        with open(PROCESSED_FILE, "r") as f:
            return json.load(f)

    except (json.JSONDecodeError, OSError):
        print("⚠️ processed_files.json is empty or invalid.")
        print("🔄 Starting with a fresh file.")
        return {}


def save_processed_files(processed):

    with open(PROCESSED_FILE, "w") as f:
        json.dump(
            processed,
            f,
            indent=4
        )


def ingest():

    processed = load_processed_files()

    pdf_files = list(DATA_PATH.rglob("*.pdf"))

    print(f"PDF files found: {len(pdf_files)}")

    for pdf_file in pdf_files:

        file_hash = calculate_hash(pdf_file)

        file_key = str(pdf_file)

        # Already processed
        if file_key in processed:

            if processed[file_key] == file_hash:

                print(f"⏭️ Skipping: {pdf_file.name}")

                continue

        print(f"📥 Loading: {pdf_file.name}")

        documents = load_pdf(pdf_file)

        chunks = split_documents(documents)

        print(f"   Chunks: {len(chunks)}")

        if chunks:

            add_documents(chunks)

            processed[file_key] = file_hash

            save_processed_files(processed)

            print(f"✅ Stored: {pdf_file.name}")


if __name__ == "__main__":

    ingest()