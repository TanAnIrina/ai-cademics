"""Build a PDF export of an archived session, including a statistics summary.

Uses fpdf2 (pure-Python). The PDF is generated on demand from the archive's JSON
payload, so no chart images are stored; emotion data is rendered as compact
tables instead.
"""
from __future__ import annotations

from fpdf import FPDF

EMOTIONS = ("happiness", "frustration", "confidence", "curiosity", "boredom", "anxiety")
SLOT_LABEL = {"teacher": "Teacher", "student_a": "Student A", "student_b": "Student B",
              "student_c": "Student C", "student_d": "Student D", "student_e": "Student E"}


def _ascii(text: object) -> str:
    """fpdf core fonts are latin-1; drop anything outside it (e.g. emoji, smart quotes)."""
    s = str(text)
    repl = {"\u2014": "-", "\u2013": "-", "\u2026": "...", "\u2019": "'",
            "\u201c": '"', "\u201d": '"', "\u2018": "'"}
    for a, b in repl.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "ignore").decode("latin-1")


class _Report(FPDF):
    def header(self) -> None:  # pragma: no cover - visual
        pass

    def footer(self) -> None:  # pragma: no cover - visual
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140)
        self.cell(0, 8, f"AI-cademics - page {self.page_no()}", align="C")


def _h1(pdf: _Report, text: str) -> None:
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(20)
    pdf.multi_cell(0, 8, _ascii(text), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _h2(pdf: _Report, text: str) -> None:
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30)
    pdf.cell(0, 7, _ascii(text), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(210)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(2)


def _body(pdf: _Report, text: str, size: int = 10) -> None:
    pdf.set_font("Helvetica", "", size)
    pdf.set_text_color(40)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5, _ascii(text), new_x="LMARGIN", new_y="NEXT")


def build_pdf(archive: dict) -> bytes:
    s = archive.get("session", {})
    room = s.get("classroom", {})
    pdf = _Report(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- header ---
    _h1(pdf, f"AI-cademics - {archive.get('name', 'Session')}")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90)
    meta = (
        f"Subject: {room.get('subject') or '-'}    "
        f"Sprints: {archive.get('num_sprints', '-')}    "
        f"Students: {room.get('max_students', '-')}    "
        f"Finished: {archive.get('finished_at', '-')[:19].replace('T', ' ')}"
    )
    pdf.multi_cell(0, 5, _ascii(meta), new_x="LMARGIN", new_y="NEXT")

    grades = s.get("grades", [])
    journals = s.get("journals", [])
    evals = s.get("evals", [])
    passed = sum(1 for e in evals if e.get("passed"))

    # --- summary ---
    _h2(pdf, "Summary")
    _body(pdf,
          f"Messages: {len(s.get('transcript', []))}    Grades: {len(grades)}    "
          f"Journals: {len(journals)}    Evals passed: {passed}/{len(evals)}")

    # --- grades ---
    if grades:
        _h2(pdf, "Grades")
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(238, 238, 238)
        pdf.cell(20, 6, "Sprint", border=1, fill=True)
        pdf.cell(60, 6, "Student", border=1, fill=True)
        pdf.cell(20, 6, "Grade", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for g in grades:
            pdf.cell(20, 6, _ascii(g.get("sprint", "")), border=1)
            pdf.cell(60, 6, _ascii(g.get("student", "")), border=1)
            pdf.cell(20, 6, _ascii(g.get("grade", "")), border=1, new_x="LMARGIN", new_y="NEXT")

    # --- statistics: final emotions per agent ---
    timeline = s.get("emotion_timeline", [])
    if timeline:
        _h2(pdf, "Statistics - final emotions")
        finals: dict[str, dict] = {}
        for pt in timeline:
            finals[pt["slot"]] = pt  # later sprints overwrite -> final state
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(238, 238, 238)
        pdf.cell(40, 6, "Agent", border=1, fill=True)
        for e in EMOTIONS:
            pdf.cell(25, 6, e[:9].title(), border=1, fill=True, align="C")
        pdf.ln()
        pdf.set_font("Helvetica", "", 8)
        for slot, pt in finals.items():
            label = f"{pt.get('agent_name', '')} ({SLOT_LABEL.get(slot, slot)})"
            pdf.cell(40, 6, _ascii(label)[:24], border=1)
            for e in EMOTIONS:
                pdf.cell(25, 6, _ascii(pt.get(e, 0)), border=1, align="C")
            pdf.ln()

    # --- sanctions ---
    sanctions = s.get("sanctions", [])
    if sanctions:
        _h2(pdf, "Sanctions & rewards")
        for sc in sanctions:
            sign = "+" if sc.get("points", 0) >= 0 else ""
            _body(pdf, f"[{sign}{sc.get('points', 0)}] {sc.get('student', '')}: "
                       f"{sc.get('explanation', '')}", size=9)

    # --- ratings ---
    ratings = s.get("ratings", [])
    if ratings:
        avg = round(sum(r.get("stars", 0) for r in ratings) / len(ratings), 2)
        _h2(pdf, f"Lesson ratings - {avg}/5 from {len(ratings)} observer(s)")
        for r in ratings:
            line = f"{'*' * int(r.get('stars', 0))} ({r.get('stars', 0)}/5) {r.get('nickname', '')}"
            if r.get("comment"):
                line += f": {r['comment']}"
            _body(pdf, line, size=9)

    # --- journals ---
    if journals:
        _h2(pdf, "Journals")
        for j in journals:
            role = "Teacher" if j.get("author_role") == "teacher" else "Student"
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(30)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 5, _ascii(
                f"{j.get('student', '')} ({role}) - sprint {j.get('sprint', '')} - "
                f"{j.get('word_count', 0)} words"), new_x="LMARGIN", new_y="NEXT")
            _body(pdf, j.get("content", ""), size=9)
            pdf.ln(1)

    out = pdf.output()
    return bytes(out)
