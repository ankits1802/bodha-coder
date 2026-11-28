from __future__ import annotations

from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape

from gold_cases import PAYER_NAMES, GoldCase, GoldSet, Section, Table
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer
from reportlab.platypus import Table as GridTable

__all__ = ["render_note"]

MARGIN = 0.7 * inch
FOOTER = "Synthetic record for software evaluation. Not a real patient."
PLACE_NAMES = {
    "11": "Office",
    "02": "Telehealth, patient not at home",
    "10": "Telehealth, patient at home",
    "31": "Skilled nursing facility",
    "32": "Nursing facility",
}
NURSING_PLACES = frozenset({"31", "32"})
SIGNED_AT = "17:40"
RULE = colors.HexColor("#4a4a4a")
SHADE = colors.HexColor("#eeeeee")
_BASE = getSampleStyleSheet()
STYLES = {
    "practice": ParagraphStyle("practice", parent=_BASE["Title"], fontSize=15, leading=18, spaceAfter=0),
    "contact": ParagraphStyle("contact", parent=_BASE["Normal"], fontSize=8.5, alignment=1, textColor=RULE),
    "title": ParagraphStyle("title", parent=_BASE["Heading2"], fontSize=12, spaceBefore=8, spaceAfter=4),
    "heading": ParagraphStyle("heading", parent=_BASE["Heading4"], fontSize=10, spaceBefore=7, spaceAfter=2),
    "body": ParagraphStyle("body", parent=_BASE["Normal"], fontSize=9.5, leading=12.5),
    "cell": ParagraphStyle("cell", parent=_BASE["Normal"], fontSize=8.5, leading=10.5),
    "signature": ParagraphStyle("signature", parent=_BASE["Normal"], fontSize=9, spaceBefore=12, textColor=RULE),
}


def render_note(case: GoldCase, gold: GoldSet) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=f"Visit note {case.id}",
        author=gold.letterhead.name,
        invariant=1,
    )
    story = [*_letterhead(gold), *_banner(case, gold), *_sections(case.sections, _signature(case, gold))]
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def _letterhead(gold: GoldSet) -> list[Flowable]:
    contact = f"{gold.letterhead.address}  |  Phone {gold.letterhead.phone}"
    return [
        Paragraph(escape(gold.letterhead.name), STYLES["practice"]),
        Paragraph(escape(contact), STYLES["contact"]),
        Spacer(1, 6),
    ]


def _banner(case: GoldCase, gold: GoldSet) -> list[Flowable]:
    provider = gold.providers[case.visit.provider]
    born = date(case.visit.service_date.year - case.patient.age, 1, 1)
    rows = [
        ("Patient", case.patient_label, "MRN", case.mrn),
        ("Date of birth", f"{_day(born)} ({case.patient.age} y)", "Sex", case.patient.sex.title()),
        ("Date of service", _day(case.visit.service_date), "Visit", case.visit.visit_type),
        ("Provider", provider.signature, "Specialty", provider.specialty),
        ("Location", _location(case, gold), "Coverage", PAYER_NAMES[case.visit.payer]),
    ]
    table = GridTable([[_cell(text) for text in row] for row in rows], colWidths=[1.0 * inch, 2.55 * inch] * 2)
    table.setStyle(
        [
            ("BOX", (0, 0), (-1, -1), 0.8, RULE),
            ("BACKGROUND", (0, 0), (0, -1), SHADE),
            ("BACKGROUND", (2, 0), (2, -1), SHADE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
    )
    return [table, Paragraph(_note_title(case), STYLES["title"])]


def _sections(sections: tuple[Section, ...], signature: Paragraph) -> list[Flowable]:
    blocks = [_section_parts(section) for section in sections]
    blocks[-1].append(signature)
    return [KeepTogether(parts) for parts in blocks]


def _section_parts(section: Section) -> list[Flowable]:
    parts: list[Flowable] = [Paragraph(escape(section.heading), STYLES["heading"])]
    if section.text:
        parts += [Paragraph(escape(line), STYLES["body"]) for line in section.text.split("\n")]
    if section.table:
        parts.append(_grid(section.table))
    return parts


def _grid(table: Table) -> GridTable:
    rows = [[_cell(text, bold=True) for text in table.columns], *[[_cell(text) for text in row] for row in table.rows]]
    grid = GridTable(rows, hAlign="LEFT", repeatRows=1)
    grid.setStyle(
        [
            ("GRID", (0, 0), (-1, -1), 0.5, RULE),
            ("BACKGROUND", (0, 0), (-1, 0), SHADE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
    )
    return grid


def _signature(case: GoldCase, gold: GoldSet) -> Paragraph:
    signed = f"Electronically signed by {gold.providers[case.visit.provider].signature}"
    return Paragraph(escape(f"{signed} on {_day(case.visit.service_date)} at {SIGNED_AT}."), STYLES["signature"])


def _footer(canvas: Canvas, document: SimpleDocTemplate) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(RULE)
    canvas.drawString(MARGIN, 0.45 * inch, FOOTER)
    canvas.drawRightString(letter[0] - MARGIN, 0.45 * inch, f"Page {document.page}")
    canvas.restoreState()


def _location(case: GoldCase, gold: GoldSet) -> str:
    place = case.visit.place_of_service
    site = gold.facility.name if place in NURSING_PLACES else gold.letterhead.name
    return f"{site}, {PLACE_NAMES[place]} (POS {place})"


def _note_title(case: GoldCase) -> str:
    if case.visit.place_of_service in NURSING_PLACES:
        return "Nursing facility visit note"
    if PLACE_NAMES[case.visit.place_of_service].startswith("Telehealth"):
        return "Telehealth visit note"
    return "Office visit note"


def _cell(text: str, *, bold: bool = False) -> Paragraph:
    shown = f"<b>{escape(text)}</b>" if bold else escape(text)
    return Paragraph(shown, STYLES["cell"])


def _day(value: date) -> str:
    return value.strftime("%m/%d/%Y")
