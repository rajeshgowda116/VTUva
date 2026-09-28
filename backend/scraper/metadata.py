import re
from datetime import datetime
from typing import Dict, Any, Optional

# Regex Patterns for VTU Metadata Extraction
SUBJECT_CODE_REGEX = re.compile(r"\b(1[5-9]|2[0-5])[A-Z]{2,4}\d{2,3}[A-Z]?\b", re.IGNORECASE)
SCHEME_REGEX = re.compile(r"\b(2015|2017|2018|2021|2022|2024)\s*(scheme|syllabus)?\b", re.IGNORECASE)
SEMESTER_REGEX = re.compile(r"\b([1-8])(?:st|nd|rd|th)?\s*(?:sem|semester)\b", re.IGNORECASE)
BRANCH_REGEX = re.compile(
    r"\b(CSE|ECE|ISE|ME|EEE|CIVIL|AIML|AI\s*&\s*DS|BT|BME|AE|ROBOTICS|DATA SCIENCE|CYBER SECURITY)\b",
    re.IGNORECASE
)
ACADEMIC_YEAR_REGEX = re.compile(r"\b(20\d{2}\s*[-–/]\s*20?\d{2})\b")
DATE_REGEX = re.compile(r"\b(\d{1,2}[-/.](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{1,2})[-/.](?:20)?\d{2})\b", re.IGNORECASE)

DOC_TYPE_KEYWORDS = {
    "circular": ["circular", "notification", "announcement", "notice"],
    "syllabus": ["syllabus", "curriculum", "scheme of study", "course structure"],
    "timetable": ["timetable", "time table", "exam schedule", "examination schedule"],
    "results": ["results", "rank list", "revaluation"],
    "regulations": ["regulations", "statute", "ordinance"],
    "academic_calendar": ["calendar of events", "academic calendar"],
}


def extract_metadata(
    url: str,
    title: str,
    content_text: str,
    content_type: str,
    content_hash: str,
    scraped_at: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Extracts structured, reliable VTU metadata from page text, title, and URL.
    Only populates fields when matching patterns are found.
    """
    combined_text = f"{title}\n{url}\n{content_text[:4000]}"
    
    metadata: Dict[str, Any] = {
        "source": "VTU Official Website",
        "url": url,
        "title": title or "VTU Official Page",
        "content_type": content_type,
        "document_type": "general",
        "branch": "",
        "semester": "",
        "subject": "",
        "subject_code": "",
        "scheme": "",
        "module": "",
        "academic_year": "",
        "published_date": "",
        "scraped_at": (scraped_at or datetime.utcnow()).isoformat(),
        "content_hash": content_hash,
    }

    # 1. Document Type Detection
    lower_comb = combined_text.lower()
    for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
        if any(kw in lower_comb for kw in keywords):
            metadata["document_type"] = doc_type
            break

    # 2. Subject Code
    subj_match = SUBJECT_CODE_REGEX.search(combined_text)
    if subj_match:
        metadata["subject_code"] = subj_match.group(0).upper()

    # 3. Scheme
    scheme_match = SCHEME_REGEX.search(combined_text)
    if scheme_match:
        metadata["scheme"] = scheme_match.group(1)

    # 4. Semester
    sem_match = SEMESTER_REGEX.search(combined_text)
    if sem_match:
        metadata["semester"] = f"{sem_match.group(1)}th Semester" if sem_match.group(1) not in ("1", "2", "3") else f"{sem_match.group(1)}st Semester" if sem_match.group(1) == "1" else f"{sem_match.group(1)}nd Semester" if sem_match.group(1) == "2" else "3rd Semester"

    # 5. Branch
    branch_match = BRANCH_REGEX.search(combined_text)
    if branch_match:
        metadata["branch"] = branch_match.group(0).upper()

    # 6. Academic Year
    ay_match = ACADEMIC_YEAR_REGEX.search(combined_text)
    if ay_match:
        metadata["academic_year"] = ay_match.group(0)

    # 7. Date
    date_match = DATE_REGEX.search(combined_text)
    if date_match:
        metadata["published_date"] = date_match.group(0)

    return metadata
