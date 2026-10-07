import sqlite3, re, os

def get_pyq_context_from_db(question: str, subject_code: str = "") -> str:
    # Detect subject code from question if not explicitly provided
    code_match = re.search(r"\b([A-Z]{2,5}\d{2,4}[A-Z]?)\b", question.upper())
    subj = code_match.group(1) if code_match else (subject_code.upper() if subject_code else "")

    if not subj or subj in ("GENERAL", "ALL"):
        return ""

    try:
        db_path = 'vtuva.db'
        if not os.path.exists(db_path):
            db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'vtuva.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query pyq_questions
        cursor.execute(
            "SELECT main_question, sub_question, question_text, marks, year, session "
            "FROM pyq_questions WHERE UPPER(subject_code) LIKE ? ORDER BY id",
            (f"%{subj}%",)
        )
        questions = cursor.fetchall()

        # Query pyq_question_groups
        cursor.execute(
            "SELECT canonical_question, repetition_count, years_asked, importance_tier "
            "FROM pyq_question_groups WHERE UPPER(subject_code) LIKE ? ORDER BY repetition_count DESC",
            (f"%{subj}%",)
        )
        groups = cursor.fetchall()
        conn.close()

        if not questions and not groups:
            return ""

        def parse_module(main_q_str):
            if not main_q_str: return 1
            num_match = re.search(r"\d+", str(main_q_str))
            if not num_match: return 1
            n = int(num_match.group(0))
            if n in (1, 2): return 1
            elif n in (3, 4): return 2
            elif n in (5, 6): return 3
            elif n in (7, 8): return 4
            elif n in (9, 10): return 5
            return 1

        lines = [f"=== STRUCTURED PREVIOUS YEAR QUESTIONS (PYQs) FOR SUBJECT: {subj} ==="]

        if groups:
            lines.append("\n### Most Repeated / High-Frequency Questions:")
            for g in groups:
                canon_q, rep_cnt, years, tier = g
                lines.append(f"- **[Repeated {rep_cnt}x | Years: {years}]** {canon_q} ({tier})")

        if questions:
            lines.append("\n### PYQ Items by VTU Exam Module:")
            by_mod = {1: [], 2: [], 3: [], 4: [], 5: []}
            seen_texts = set()
            for q in questions:
                mq, sq, text, marks, year, sess = q
                m_num = parse_module(mq)
                clean_t = text.strip()
                if clean_t not in seen_texts:
                    seen_texts.add(clean_t)
                    by_mod[m_num].append(f"• **[{mq}{sq if sq else ''}]** {clean_t} ({marks} Marks)")

            for m_i in range(1, 6):
                if by_mod[m_i]:
                    lines.append(f"\n#### Module {m_i}:")
                    for q_item in by_mod[m_i]:
                        lines.append(q_item)

        return "\n".join(lines)
    except Exception as e:
        print(f"[DB PYQ Lookup Error]: {e}")
        return ""

print(get_pyq_context_from_db("Can you show top repeated PYQs for BCS502?"))
