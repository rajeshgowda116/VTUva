import sqlite3

conn = sqlite3.connect('vtuva.db')
cursor = conn.cursor()

print("=== Searching pyq_question_groups for BCS502 ===")
cursor.execute("SELECT id, subject_code, module, canonical_question, repetition_count, years_asked, importance_tier FROM pyq_question_groups WHERE subject_code LIKE '%BCS502%' OR subject_code LIKE '%502%' ORDER BY module, repetition_count DESC")
rows = cursor.fetchall()
print(f"Found {len(rows)} groups for BCS502:")
for r in rows:
    print(r)

print("\n=== Searching pyq_questions for BCS502 ===")
cursor.execute("SELECT module, main_question, sub_question, question_text, marks FROM pyq_questions WHERE subject_code LIKE '%BCS502%' OR subject_code LIKE '%502%' LIMIT 20")
rows = cursor.fetchall()
print(f"Found {len(rows)} questions for BCS502:")
for r in rows:
    print(r)
