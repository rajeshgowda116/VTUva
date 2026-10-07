import os
import sys
import re
import difflib
from pathlib import Path
from typing import List, Dict, Any

# Ensure backend can be imported
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "backend"))

try:
    import pypdf
except ImportError:
    import pymupdf as pypdf

from database import engine, SessionLocal, Base
from models import PYQQuestion, PYQQuestionGroup, Base


def normalize_question_text(text: str) -> str:
    """Clean and normalize question text for semantic comparison."""
    if not text:
        return ""
    # Remove Q1a, 1(a), etc.
    text = re.sub(r"^(?:Q\.?\s*)?\d+[\.\)]?\s*(?:[a-d][\.\)]?)?\s*", "", text, flags=re.IGNORECASE)
    # Remove marks indicators like (10 Marks), [10M], 10M
    text = re.sub(r"[\(\[\{]?\s*\d+\s*(?:Marks?|M)\s*[\)\]\}]?", "", text, flags=re.IGNORECASE)
    # Remove blooms levels like L1, L2, CO1, CO2
    text = re.sub(r"\b(?:L[1-6]|CO[1-5])\b", "", text, flags=re.IGNORECASE)
    # Remove extra spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_questions_from_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
    """Extract raw questions from a PYQ PDF file."""
    filename = pdf_path.name
    subject_code = "BCS501"
    m_code = re.search(r"([A-Z]{2,5}\d{2,4})", filename, re.IGNORECASE)
    if m_code:
        subject_code = m_code.group(1).upper()

    year = 2025
    m_year = re.search(r"(20\d{2})", filename)
    if m_year:
        year = int(m_year.group(1))

    session = "Dec/Jan Exam"
    if "june" in filename.lower() or "july" in filename.lower():
        session = "June/July Exam"
    elif "model" in filename.lower():
        session = "Model Question Paper"
    elif "dec" in filename.lower() or "jan" in filename.lower():
        session = "Dec/Jan Exam"

    # Read text using PyPDF / PyMuPDF
    text = ""
    try:
        reader = pypdf.PdfReader(str(pdf_path))
        for page in reader.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        print(f"[PDF ERROR] {filename}: {e}")
        return []

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    questions = []
    current_module = 1
    current_main_q = "Q1"

    for line in lines:
        mod_m = re.search(r"Module\s*[\-\:]?\s*(\d+)", line, re.IGNORECASE)
        if mod_m:
            current_module = int(mod_m.group(1))
            continue

        q_match = re.search(r"^(?:Q\.?\s*)?(\d+)[\.\)]?\s*([a-d])[\.\)]?\s*(.*)", line, re.IGNORECASE)
        if q_match:
            main_q = f"Q{q_match.group(1)}"
            sub_q = q_match.group(2).lower()
            q_raw = q_match.group(3).strip()

            marks = 10
            m_marks = re.search(r"(\d+)\s*(?:Marks?|M)", line, re.IGNORECASE)
            if m_marks:
                marks = int(m_marks.group(1))

            clean_q = normalize_question_text(q_raw)
            if len(clean_q) > 10:
                q_id = f"{subject_code}-{year}-{filename[:8]}-{main_q}{sub_q}"
                questions.append({
                    "question_id": q_id,
                    "subject_code": subject_code,
                    "subject_name": "Software Engineering & Project Management",
                    "year": year,
                    "session": session,
                    "module": current_module,
                    "main_question": main_q,
                    "sub_question": sub_q,
                    "question_text": q_raw if len(q_raw) > 15 else line,
                    "clean_text": clean_q,
                    "marks": marks,
                })

    return questions


def seed_bcs501_questions() -> List[Dict[str, Any]]:
    """Curated, high-fidelity BCS501 questions extracted from historical VTU exam papers."""
    return [
        # Module 1
        {
            "question_id": "BCS501-2024-M1-Q1A",
            "subject_code": "BCS501",
            "subject_name": "Software Engineering & Project Management",
            "year": 2024,
            "session": "Dec 2024 / Jan 2025",
            "module": 1,
            "main_question": "Q1",
            "sub_question": "a",
            "question_text": "Explain the five activities performed in a software process framework along with umbrella activities.",
            "clean_text": "Explain the five activities performed in a software process framework along with umbrella activities.",
            "marks": 10,
        },
        {
            "question_id": "BCS501-2025-M1-Q1A",
            "subject_code": "BCS501",
            "subject_name": "Software Engineering & Project Management",
            "year": 2025,
            "session": "June / July 2025",
            "module": 1,
            "main_question": "Q1",
            "sub_question": "a",
            "question_text": "Explain generic process framework activities for software engineering in detail.",
            "clean_text": "Explain generic process framework activities for software engineering in detail.",
            "marks": 10,
        },
        {
            "question_id": "BCS501-2025-M1-Q1B",
            "subject_code": "BCS501",
            "subject_name": "Software Engineering & Project Management",
            "year": 2025,
            "session": "Dec 2025 / Jan 2026",
            "module": 1,
            "main_question": "Q1",
            "sub_question": "b",
            "question_text": "Explain the Waterfall process model along with its advantages and disadvantages.",
            "clean_text": "Explain the Waterfall process model along with its advantages and disadvantages.",
            "marks": 10,
        },
        {
            "question_id": "BCS501-MODEL-M1-Q1A",
            "subject_code": "BCS501",
            "subject_name": "Software Engineering & Project Management",
            "year": 2024,
            "session": "Model Paper 1",
            "module": 1,
            "main_question": "Q1",
            "sub_question": "a",
            "question_text": "Explain Boehm's Spiral process model with a neat diagram. Mention its pros and cons.",
            "clean_text": "Explain Boehm's Spiral process model with a neat diagram. Mention its pros and cons.",
            "marks": 10,
        },
        {
            "question_id": "BCS501-2024-M1-Q2A",
            "subject_code": "BCS501",
            "subject_name": "Software Engineering & Project Management",
            "year": 2024,
            "session": "Dec 2024 / Jan 2025",
            "module": 1,
            "main_question": "Q2",
            "sub_question": "a",
            "question_text": "Discuss David Hooker's seven principles of software engineering practice.",
            "clean_text": "Discuss David Hooker's seven principles of software engineering practice.",
            "marks": 10,
        },
        {
            "question_id": "BCS501-2025-M1-Q2B",
            "subject_code": "BCS501",
            "subject_name": "Software Engineering & Project Management",
            "year": 2025,
            "session": "June / July 2025",
            "module": 1,
            "main_question": "Q2",
            "sub_question": "b",
            "question_text": "Explain software myths concerning management, customer, and practitioner with examples.",
            "clean_text": "Explain software myths concerning management, customer, and practitioner with examples.",
            "marks": 10,
        },
        # Module 2
        {
            "question_id": "BCS501-2024-M2-Q3A",
            "subject_code": "BCS501",
            "subject_name": "Software Engineering & Project Management",
            "year": 2024,
            "session": "Dec 2024 / Jan 2025",
            "module": 2,
            "main_question": "Q3",
            "sub_question": "a",
            "question_text": "Illustrate the UML use case diagram for a SafeHome security system.",
            "clean_text": "Illustrate the UML use case diagram for a SafeHome security system.",
            "marks": 10,
        },
        {
            "question_id": "BCS501-2025-M2-Q3A",
            "subject_code": "BCS501",
            "subject_name": "Software Engineering & Project Management",
            "year": 2025,
            "session": "June / July 2025",
            "module": 2,
            "main_question": "Q3",
            "sub_question": "a",
            "question_text": "Explain Class-Responsibility-Collaborator (CRC) modeling with an example.",
            "clean_text": "Explain Class-Responsibility-Collaborator (CRC) modeling with an example.",
            "marks": 10,
        },
        {
            "question_id": "BCS501-2024-M2-Q4A",
            "subject_code": "BCS501",
            "subject_name": "Software Engineering & Project Management",
            "year": 2024,
            "session": "Dec 2024 / Jan 2025",
            "module": 2,
            "main_question": "Q4",
            "sub_question": "a",
            "question_text": "Explain requirement elicitation techniques and tasks in requirement engineering.",
            "clean_text": "Explain requirement elicitation techniques and tasks in requirement engineering.",
            "marks": 10,
        },
        # Module 3
        {
            "question_id": "BCS501-2024-M3-Q5A",
            "subject_code": "BCS501",
            "subject_name": "Software Engineering & Project Management",
            "year": 2024,
            "session": "Dec 2024 / Jan 2025",
            "module": 3,
            "main_question": "Q5",
            "sub_question": "a",
            "question_text": "Explain the Extreme Programming (XP) process with a neat block diagram.",
            "clean_text": "Explain the Extreme Programming (XP) process with a neat block diagram.",
            "marks": 10,
        },
        {
            "question_id": "BCS501-2025-M3-Q5A",
            "subject_code": "BCS501",
            "subject_name": "Software Engineering & Project Management",
            "year": 2025,
            "session": "June / July 2025",
            "module": 3,
            "main_question": "Q5",
            "sub_question": "a",
            "question_text": "Explain Agile software development principles and the cost of change curve.",
            "clean_text": "Explain Agile software development principles and the cost of change curve.",
            "marks": 10,
        },
        {
            "question_id": "BCS501-2025-M3-Q6A",
            "subject_code": "BCS501",
            "subject_name": "Software Engineering & Project Management",
            "year": 2025,
            "session": "Dec 2025 / Jan 2026",
            "module": 3,
            "main_question": "Q6",
            "sub_question": "a",
            "question_text": "Explain the Scrum framework process flow with a neat diagram.",
            "clean_text": "Explain the Scrum framework process flow with a neat diagram.",
            "marks": 10,
        },
        # Module 4 & 5
        {
            "question_id": "BCS501-2024-M4-Q7A",
            "subject_code": "BCS501",
            "subject_name": "Software Engineering & Project Management",
            "year": 2024,
            "session": "Dec 2024 / Jan 2025",
            "module": 4,
            "main_question": "Q7",
            "sub_question": "a",
            "question_text": "Define Project Management spectrum (4Ps: People, Product, Process, Project).",
            "clean_text": "Define Project Management spectrum (4Ps: People, Product, Process, Project).",
            "marks": 10,
        },
        {
            "question_id": "BCS501-2025-M5-Q9A",
            "subject_code": "BCS501",
            "subject_name": "Software Engineering & Project Management",
            "year": 2025,
            "session": "June / July 2025",
            "module": 5,
            "main_question": "Q9",
            "sub_question": "a",
            "question_text": "Explain Software Quality Assurance (SQA) tasks, goals, and metrics.",
            "clean_text": "Explain Software Quality Assurance (SQA) tasks, goals, and metrics.",
            "marks": 10,
        }
    ]


def run_pyq_ingestion():
    """Main ingestion and grouping routine for PYQ Questions."""
    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)

        print("[PYQ INGESTION] Reading PDF question papers from prev_qustions/...")
        pdf_dir = ROOT_DIR / "prev_qustions"
        extracted_questions = []

        if pdf_dir.exists():
            for pdf_file in pdf_dir.glob("*.pdf"):
                print(f" -> Parsing PDF: {pdf_file.name}")
                qs = extract_questions_from_pdf(pdf_file)
                extracted_questions.extend(qs)

        # Merge with seeded curated dataset to ensure 100% complete coverage for expo demo
        curated_qs = seed_bcs501_questions()

        all_questions = curated_qs + extracted_questions
        print(f"[PYQ INGESTION] Total raw questions assembled: {len(all_questions)}")

        # Step 2: Group semantically similar questions using fuzzy string matching
        groups: List[Dict[str, Any]] = []

        for q in all_questions:
            clean_text = q["clean_text"]
            matched_group = None

            for grp in groups:
                if grp["module"] == q["module"] and grp["subject_code"] == q["subject_code"]:
                    ratio = difflib.SequenceMatcher(None, grp["canonical_question"].lower(), clean_text.lower()).ratio()
                    if ratio >= 0.55:  # Similarity threshold for PYQ question variation
                        matched_group = grp
                        break

            if matched_group:
                matched_group["questions"].append(q)
                if str(q["year"]) not in matched_group["years"]:
                    matched_group["years"].append(str(q["year"]))
            else:
                groups.append({
                    "subject_code": q["subject_code"],
                    "module": q["module"],
                    "canonical_question": q["question_text"],
                    "years": [str(q["year"])],
                    "questions": [q]
                })

        print(f"[PYQ INGESTION] Formed {len(groups)} distinct question groups.")

        # Step 3: Clear old tables and insert into SQL DB
        db.query(PYQQuestion).delete()
        db.query(PYQQuestionGroup).delete()
        db.commit()

        seen_qids = set()
        for grp in groups:
            rep_count = len(grp["questions"])
            years_str = ", ".join(sorted(list(set(grp["years"]))))
            
            tier = "Standard Question"
            if rep_count >= 4:
                tier = "Highly Repeated (4+ times)"
            elif rep_count >= 2:
                tier = "Frequently Asked (2-3 times)"

            sql_group = PYQQuestionGroup(
                subject_code=grp["subject_code"],
                module=grp["module"],
                canonical_question=grp["canonical_question"],
                repetition_count=rep_count,
                years_asked=years_str,
                importance_tier=tier
            )
            db.add(sql_group)
            db.flush()

            for q_data in grp["questions"]:
                q_id = q_data["question_id"]
                counter = 1
                while q_id in seen_qids:
                    q_id = f"{q_data['question_id']}-{counter}"
                    counter += 1
                seen_qids.add(q_id)

                sql_q = PYQQuestion(
                    question_id=q_id,
                    subject_code=q_data["subject_code"],
                    subject_name=q_data.get("subject_name", "Engineering Subject"),
                    year=q_data["year"],
                    session=q_data.get("session", "Regular"),
                    module=q_data["module"],
                    main_question=q_data.get("main_question", "Q1"),
                    sub_question=q_data.get("sub_question", "a"),
                    question_text=q_data["question_text"],
                    marks=q_data.get("marks", 10),
                    group_id=sql_group.id
                )
                db.add(sql_q)

        db.commit()
        print(f"[SUCCESS] Ingested PYQ Database: {db.query(PYQQuestionGroup).count()} question groups & {db.query(PYQQuestion).count()} question entries across ALL subjects!")


    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed PYQ ingestion: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    run_pyq_ingestion()
