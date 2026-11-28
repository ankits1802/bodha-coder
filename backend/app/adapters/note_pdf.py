from __future__ import annotations

import re
from html.parser import HTMLParser

from app.adapters.pdf_writer import PdfDocument, PdfText, render_pdf

__all__ = ["NOTE_TITLE", "html_text", "text_note_pdf"]

NOTE_TITLE = "Visit note"
SKIPPED_TAGS = frozenset({"script", "style", "head", "title", "template", "noscript"})
BLOCK_TAGS = frozenset(
    {
        "address",
        "article",
        "blockquote",
        "br",
        "dd",
        "div",
        "dl",
        "dt",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "td",
        "th",
        "tr",
        "ul",
    }
)
SPACES = re.compile(r"[ \t\f\v\r]+")
BLANK_LINES = re.compile(r"\n\s*\n+")


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in SKIPPED_TAGS:
            self.hidden += 1
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIPPED_TAGS:
            self.hidden = max(0, self.hidden - 1)
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def html_text(markup: str) -> str:
    parser = _VisibleText()
    parser.feed(markup)
    parser.close()
    return _tidy("".join(parser.parts))


def text_note_pdf(text: str) -> bytes:
    paragraphs = [part for part in BLANK_LINES.split(_tidy(text)) if part.strip()]
    if not paragraphs:
        raise ValueError("the note has no text")
    blocks = tuple(PdfText(paragraph) for paragraph in paragraphs)
    return render_pdf(PdfDocument(title=NOTE_TITLE, footer=NOTE_TITLE, blocks=blocks, reproducible=True))


def _tidy(text: str) -> str:
    lines = [SPACES.sub(" ", line).strip() for line in text.replace("\r\n", "\n").split("\n")]
    return BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()
