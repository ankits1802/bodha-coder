from __future__ import annotations

from gold_cases import load_gold_set
from gold_pdf import FOOTER, render_note

from app.adapters.pdf_text import read_pdf_text


def test_a_rendered_note_is_a_stable_pdf_whose_text_bodha_can_read():
    gold = load_gold_set()
    case = gold.case("GS-06")
    first, second = render_note(case, gold), render_note(case, gold)
    assert first.startswith(b"%PDF") and first == second
    document = read_pdf_text(first)
    assert document.has_text_layer
    for expected in ("Synthetic Patient 06", "SYN-0006-ZZ", "Medicare Part B", "Medication", "95 minutes", FOOTER):
        assert expected in document.text


def test_every_case_renders_with_its_tables():
    gold = load_gold_set()
    texts = {case.id: read_pdf_text(render_note(case, gold)).text for case in gold.cases}
    assert all("Assessment and plan" in text for text in texts.values())
    assert "Before supper" in texts["GS-47"]
    assert "Telehealth, patient at home (POS 10)" in texts["GS-29"].replace("\n", " ")
