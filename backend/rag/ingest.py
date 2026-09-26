import hashlib
import json
import os
import sys
import glob
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "backend"))
sys.path.insert(0, str(ROOT_DIR / "backend" / "rag"))

try:
    from backend.rag.loader import lazy_load_pdf
    from backend.rag.splitter import split_documents
    from backend.rag.vectordb import add_documents
    from backend.pyq_processor import PYQProcessor
except ImportError:
    from loader import lazy_load_pdf
    from splitter import split_documents
    from vectordb import add_documents
    from pyq_processor import PYQProcessor

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Project Directory Paths
DATA_PATH = ROOT_DIR / "data"
PREV_QUESTIONS_PATH = ROOT_DIR / "prev_qustions"
PROCESSED_FILE = Path(__file__).resolve().parent / "processed_files.json"

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
        return {}

def save_processed_files(processed):
    with open(PROCESSED_FILE, "w") as f:
        json.dump(processed, f, indent=4)

def process_and_summarize_pyqs():
    """
    Scans prev_qustions/ directory for Question Paper PDFs across ALL subjects,
    parses questions using PYQProcessor, clusters repetitions per subject code, 
    and ingests metadata summaries into ChromaDB.
    """
    processor = PYQProcessor()
    
    # Collect all PDFs from prev_qustions directory (and data/prev_qustions if present)
    pyq_files = list(PREV_QUESTIONS_PATH.rglob("*.pdf")) if PREV_QUESTIONS_PATH.exists() else []
    if DATA_PATH.exists():
        pyq_files.extend(list(DATA_PATH.rglob("*prev_qustion*.pdf")))
        pyq_files.extend(list(DATA_PATH.rglob("*pyq*.pdf")))

    # Deduplicate
    pyq_files = list(set(pyq_files))
    print(f"📄 Found {len(pyq_files)} PYQ Paper PDFs in prev_qustions directory.")
    
    subject_questions = {}
    pyq_docs = []

    for pdf_path in pyq_files:
        print(f"[PYQ Processor] Parsing Paper: {pdf_path.name}")
        try:
            result = processor.process_paper(str(pdf_path))
            subj_code = result["metadata"]["subject_code"]
            if subj_code not in subject_questions:
                subject_questions[subj_code] = []
            
            for q in result["questions"]:
                q["paper_label"] = result["metadata"]["filename"]
                subject_questions[subj_code].append(q)

            rel_path = str(pdf_path.relative_to(ROOT_DIR)) if ROOT_DIR in pdf_path.parents else pdf_path.name
            pyq_docs.append({
                "text": f"Subject {subj_code} Question Paper ({result['metadata']['filename']}):\n\n{result['raw_markdown']}",
                "page": 1,
                "source": rel_path
            })
        except Exception as e:
            print(f"[Warning] Error parsing PYQ {pdf_path.name}: {e}")

    if subject_questions:
        print("🧠 Running Semantic Similarity Analysis on prev_qustions...")
        model = SentenceTransformer("all-MiniLM-L6-v2")

        for subj_code, qs in subject_questions.items():
            if not qs:
                continue

            texts = [q["question_text"] for q in qs]
            embeddings = model.encode(texts)
            sim_matrix = cosine_similarity(embeddings)

            visited = set()
            groups = []

            for i in range(len(qs)):
                if i in visited:
                    continue
                group = [qs[i]]
                visited.add(i)

                for j in range(i + 1, len(qs)):
                    if j not in visited and sim_matrix[i][j] >= 0.68:
                        group.append(qs[j])
                        visited.add(j)

                unique_papers = list(set([item["paper_label"] for item in group]))
                groups.append({
                    "question": group[0]["question_text"],
                    "module": group[0]["module"],
                    "frequency": len(unique_papers),
                    "papers": unique_papers
                })

            summary_text = f"Subject {subj_code} - Frequently Asked & Repeated Questions Analysis (from prev_qustions):\n\n"
            groups.sort(key=lambda g: g["frequency"], reverse=True)

            for g in groups:
                freq_str = f"Repeated {g['frequency']} times" if g['frequency'] > 1 else "Asked 1 time"
                summary_text += f"- [Module {g['module']}] ({freq_str}): {g['question']} (Papers: {', '.join(g['papers'])})\n"

            pyq_docs.append({
                "text": summary_text,
                "page": 1,
                "source": f"prev_qustions/{subj_code}_Most_Asked_Questions_Summary.md"
            })

    if pyq_docs:
        add_documents(pyq_docs)
        print(f"[Complete] Ingested {len(pyq_docs)} PYQ document chunks from prev_qustions into ChromaDB!")

def ingest():
    processed = load_processed_files()
    
    # 1. Standard Notes/Textbook Ingestion from data/
    notes_files = list(DATA_PATH.rglob("*.pdf")) if DATA_PATH.exists() else []
    print(f"Notes/Study PDF files found in data directory: {len(notes_files)}")

    for pdf_file in notes_files:
        file_hash = calculate_hash(pdf_file)
        file_key = str(pdf_file)

        if file_key in processed and processed[file_key] == file_hash:
            print(f"[Skipping] Already ingested: {pdf_file.name}")
            continue

        print(f"[Loading] Notes PDF: {pdf_file.name}")
        try:
            documents = list(lazy_load_pdf(pdf_file))
            chunks = split_documents(documents)
            print(f"   Chunks created: {len(chunks)}")
            if chunks:
                add_documents(chunks)
                processed[file_key] = file_hash
                save_processed_files(processed)
                print(f"[Stored] In ChromaDB: {pdf_file.name}")
        except Exception as e:
            print(f"[Warning] Error loading {pdf_file.name}: {e}")

    # 2. PYQ Ingestion strictly from prev_qustions/
    process_and_summarize_pyqs()

if __name__ == "__main__":
    ingest()