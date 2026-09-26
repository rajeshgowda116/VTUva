import re
import os
import json
import logging
from typing import List, Dict, Any, Optional
from docling.document_converter import DocumentConverter

logger = logging.getLogger("pyq_processor")

class PYQProcessor:
    """
    Universal PYQ Processing Pipeline for ALL VTU Subjects:
    1. Generic Subject & Metadata Extraction from Path & PDF Header
    2. Docling PDF Conversion (with JSON caching)
    3. Regex Question Parser, Cleaning & Module Tracking
    """

    def __init__(self, output_dir: str = "data/pyq_processed"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.converter = None  # Lazy-initialize Docling only when needed

    def _get_converter(self) -> DocumentConverter:
        if self.converter is None:
            self.converter = DocumentConverter()
        return self.converter

    @staticmethod
    def extract_metadata_from_path(pdf_path: str) -> Dict[str, Any]:
        filename = os.path.basename(pdf_path)
        
        code_match = re.search(r"([A-Z]{2,5}\d{2,4}|21[A-Z]{2,3}\d{2}|18[A-Z]{2,3}\d{2})", filename, re.IGNORECASE)
        subject_code = code_match.group(1).upper() if code_match else "UNKNOWN_SUBJECT"

        year_match = re.search(r"(20\d{2})", filename)
        year = int(year_match.group(1)) if year_match else 2024

        branch = "ENGINEERING"
        if subject_code.startswith("BCS") or subject_code.startswith("CS"):
            branch = "CSE"
        elif subject_code.startswith("BAI") or subject_code.startswith("AI"):
            branch = "AIML"
        elif subject_code.startswith("BEC") or subject_code.startswith("EC"):
            branch = "ECE"
        elif subject_code.startswith("BCHEC") or subject_code.startswith("CHE"):
            branch = "CHEMISTRY"

        session = "Standard Exam"
        if "dec" in filename.lower() or "jan" in filename.lower():
            session = "Dec/Jan Examination"
        elif "june" in filename.lower() or "july" in filename.lower():
            session = "June/July Examination"
        elif "model" in filename.lower():
            session = "Model Question Paper"

        parts = os.path.normpath(pdf_path).split(os.sep)
        if len(parts) >= 4 and parts[-4].lower() in ["pyq", "pyqs", "prev_qustions"]:
            branch = parts[-3]
            subject_code = parts[-2]

        return {
            "branch": branch,
            "subject_code": subject_code,
            "subject": subject_code,
            "year": year,
            "session": session,
            "filename": filename
        }

    def convert_pdf_to_markdown(self, pdf_path: str) -> str:
        logger.info(f"Converting PDF with Docling: {pdf_path}")
        converter = self._get_converter()
        result = converter.convert(pdf_path)
        return result.document.export_to_markdown()

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"VTU-\d{2}-\d{2}-\d{4}", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\d{2}:\d{2}:\d{2}\s*(?:am|pm)?", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\bAD\b", "", text)
        text = re.sub(r"[\s\-\.]+$", "", text)
        text = re.sub(r"^[\s\-\.]+", "", text)
        return re.sub(r"\s+", " ", text).strip()

    def parse_questions_from_markdown(self, md_content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        lines = md_content.split("\n")
        questions = []
        current_module = 1
        current_main_q = ""

        for line in lines[:15]:
            code_in_doc = re.search(r"Course\s*Code\s*[:\-]?\s*([A-Z0-9]+)", line, re.IGNORECASE)
            if code_in_doc:
                metadata["subject_code"] = code_in_doc.group(1).upper()

            title_match = re.search(r"Examination[,\s]+(.*)", line, re.IGNORECASE)
            if title_match:
                subj_title = title_match.group(1).strip()
                if len(subj_title) > 3:
                    metadata["subject"] = subj_title

        for line in lines:
            line_str = line.strip()

            mod_match = re.search(r"Module\s*[\-\:]?\s*(\d+)", line_str, re.IGNORECASE)
            if mod_match and not re.search(r"Q\.\s*\d+", line_str, re.IGNORECASE):
                current_module = int(mod_match.group(1))

            if line_str.startswith("|") and line_str.endswith("|"):
                parts = [p.strip() for p in line_str.split("|")[1:-1]]
                if len(parts) >= 3:
                    col1, col2, col3 = parts[0], parts[1], parts[2]

                    if "Module" in col1 and ("M" in parts[-1] or "C" in parts[-1] or "---" in col2):
                        mod_in_cell = re.search(r"Module\s*[\-\:]?\s*(\d+)", line_str, re.IGNORECASE)
                        if mod_in_cell:
                            current_module = int(mod_in_cell.group(1))
                        continue

                    if "---" in col1 or "---" in col2:
                        continue

                    mod_in_row = re.search(r"Module\s*[\-\:]?\s*(\d+)", col1 + " " + col2 + " " + col3, re.IGNORECASE)
                    if mod_in_row and not re.search(r"Q\.\s*\d+", col1, re.IGNORECASE):
                        current_module = int(mod_in_row.group(1))
                        continue

                    q_main_match = re.match(r"^Q\.?\s*0*(\d+)", col1, re.IGNORECASE)
                    if q_main_match:
                        current_main_q = f"Q{q_main_match.group(1)}"

                    sub_q_match = re.match(r"^([a-d])[\.\)]?", col2, re.IGNORECASE)
                    sub_q = sub_q_match.group(1).lower() if sub_q_match else ""

                    question_text = self.clean_text(col3)

                    if not question_text or question_text.upper() == "OR":
                        continue

                    marks = None
                    blooms = None
                    co = None

                    for p in parts[3:]:
                        p_clean = p.strip()
                        if p_clean.isdigit():
                            marks = int(p_clean)
                        elif re.match(r"^L[1-6]$", p_clean, re.IGNORECASE):
                            blooms = p_clean.upper()
                        elif re.match(r"^CO[1-5]$", p_clean, re.IGNORECASE):
                            co = p_clean.upper()

                    if current_main_q and question_text:
                        sub_str = f" ({sub_q})" if sub_q else ""
                        q_id = f"{metadata['subject_code']}-{metadata['year']}-{current_main_q}{sub_q}"

                        item = {
                            "question_id": q_id,
                            "subject": metadata["subject"],
                            "subject_code": metadata["subject_code"],
                            "branch": metadata["branch"],
                            "year": metadata["year"],
                            "session": metadata.get("session", ""),
                            "module": current_module,
                            "main_question": current_main_q,
                            "sub_question": sub_q,
                            "question_number": f"{current_main_q}{sub_str}",
                            "marks": marks,
                            "blooms_level": blooms,
                            "course_outcome": co,
                            "question_text": question_text
                        }
                        questions.append(item)

        return questions

    def process_paper(self, pdf_path: str, force_reprocess: bool = False) -> Dict[str, Any]:
        metadata = self.extract_metadata_from_path(pdf_path)
        out_name = f"{metadata['subject_code']}_{metadata['year']}_{os.path.basename(pdf_path)}.json"
        out_path = os.path.join(self.output_dir, out_name)

        if os.path.exists(out_path) and not force_reprocess:
            logger.info(f"⚡ Loading cached parsed JSON for {os.path.basename(pdf_path)}")
            with open(out_path, "r", encoding="utf-8") as f:
                return json.load(f)

        md_content = self.convert_pdf_to_markdown(pdf_path)
        questions = self.parse_questions_from_markdown(md_content, metadata)

        result_payload = {
            "metadata": metadata,
            "raw_markdown": md_content,
            "question_count": len(questions),
            "questions": questions
        }

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result_payload, f, indent=2)

        logger.info(f"Processed {len(questions)} questions for {metadata['subject_code']}. Saved to {out_path}")
        return result_payload
