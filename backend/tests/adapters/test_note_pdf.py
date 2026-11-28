from __future__ import annotations

from io import BytesIO

import pytest
from pypdf import PdfReader

from app.adapters.note_pdf import html_text, text_note_pdf

HTML_NOTE = """<html><head><title>Note</title><style>p { color: red }</style></head>
<body><h1>Progress note</h1><p>Assessment &amp; plan: diabetes,&nbsp;stable.</p>
<script>alert("x")</script><ul><li>Metformin</li><li>Lisinopril</li></ul></body></html>"""


def test_html_keeps_the_visible_text_in_blocks_and_drops_scripts_and_styles():
    assert html_text(HTML_NOTE) == "Progress note\n\nAssessment & plan: diabetes,\xa0stable.\n\nMetformin\n\nLisinopril"


def test_a_text_note_becomes_the_same_pdf_every_time():
    first = text_note_pdf("Progress note\n\nAssessment and plan: diabetes, stable.")
    second = text_note_pdf("Progress note\n\nAssessment and plan: diabetes, stable.")
    assert first == second
    assert first.startswith(b"%PDF")
    text = PdfReader(BytesIO(first)).pages[0].extract_text()
    assert "Assessment and plan: diabetes, stable." in text


def test_a_note_without_text_is_refused():
    with pytest.raises(ValueError):
        text_note_pdf(" \n\n ")
