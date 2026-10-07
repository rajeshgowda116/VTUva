import pypdf, glob, sys
sys.stdout.reconfigure(encoding='utf-8')

print("=== Scanning BCS502 PDFs for Module 5 Questions ===")
pdf_files = glob.glob('prev_qustions/BCS502-*.pdf')
for pdf in pdf_files:
    if "important" in pdf: continue
    try:
        reader = pypdf.PdfReader(pdf)
        txt = '\n'.join([p.extract_text() for p in reader.pages if p.extract_text()])
        print(f"\n==========================================")
        print(f"FILE: {pdf}")
        print(f"==========================================")
        lines = txt.split('\n')
        m5 = False
        for line in lines:
            if 'module' in line.lower() and ('5' in line or 'v' in line.lower()):
                m5 = True
            if m5:
                print(line)
    except Exception as e:
        print(f"Error {pdf}: {e}")
