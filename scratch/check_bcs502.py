import sqlite3
import pypdf

conn = sqlite3.connect('vtuva.db')
cursor = conn.cursor()

print("=== Checking pyq_questions subject codes ===")
cursor.execute("SELECT DISTINCT subject_code, subject_name FROM pyq_questions")
print(cursor.fetchall())

print("=== Checking pyq_question_groups ===")
cursor.execute("SELECT DISTINCT subject_code, module FROM pyq_question_groups WHERE module = 5")
print(cursor.fetchall())

print("=== Reading BCS502 PDF pages count ===")
reader = pypdf.PdfReader('prev_qustions/BCS502-important-question.pdf')
print("Page count:", len(reader.pages))
for i, page in enumerate(reader.pages):
    txt = page.extract_text()
    print(f"--- Page {i+1} ({len(txt)} chars) ---")
    if "Module 5" in txt or "Module-5" in txt or "MODULE 5" in txt or "Module V" in txt:
        print("Found Module 5 in page", i+1)
        print(txt)
