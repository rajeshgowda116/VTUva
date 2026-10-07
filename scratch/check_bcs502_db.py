import sqlite3

conn = sqlite3.connect('vtuva.db')
cursor = conn.cursor()

print("=== Checking pyq_questions for BCS502 ===")
cursor.execute("SELECT module, question_id, question_text FROM pyq_questions WHERE subject_code LIKE '%BCS502%'")
for r in cursor.fetchall():
    print(r)

print("\n=== Checking scraped_documents for BCS502 ===")
cursor.execute("SELECT title, content FROM scraped_documents WHERE content LIKE '%BCS502%' OR title LIKE '%BCS502%' LIMIT 5")
for r in cursor.fetchall():
    print(r[0])
    print(r[1][:500])
