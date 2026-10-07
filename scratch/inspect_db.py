import sqlite3
import pypdf
import os

conn = sqlite3.connect('vtuva.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables:", tables)

for (tname,) in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {tname}")
        cnt = cursor.fetchone()[0]
        print(f"Table '{tname}': {cnt} rows")
    except Exception as e:
        print(f"Error reading {tname}: {e}")

# Check for BAI151A in database tables if any
for (tname,) in tables:
    try:
        cursor.execute(f"PRAGMA table_info({tname})")
        cols = [c[1] for c in cursor.fetchall()]
        print(f"Cols in {tname}: {cols}")
        for col in cols:
            cursor.execute(f"SELECT * FROM {tname} WHERE cast({col} as text) LIKE '%BAI151A%' LIMIT 5")
            rows = cursor.fetchall()
            if rows:
                print(f"Found match in {tname}.{col}:", len(rows))
                for r in rows:
                    print("  ", r)
    except Exception as e:
        pass

pdf_path = "prev_qustions/BAI151A-important-question.pdf"
if os.path.exists(pdf_path):
    print("\n--- Extracting PDF text ---")
    try:
        reader = pypdf.PdfReader(pdf_path)
        for i, page in enumerate(reader.pages):
            print(f"--- Page {i+1} ---")
            print(page.extract_text()[:1000])
    except Exception as e:
        print("PDF Error:", e)
