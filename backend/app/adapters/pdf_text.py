from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MIN_TEXT_LAYER_CHARS = 100


class DocumentUnreadable(ValueError):
    pass


@dataclass(frozen=True)
class DocumentText:
    text: str
    pages: int

    @property
    def has_text_layer(self) -> bool:
        return len(self.text) >= MIN_TEXT_LAYER_CHARS


def read_pdf_text(pdf: bytes) -> DocumentText:
    try:
        reader = _opened(pdf)
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except PdfReadError as error:
        raise DocumentUnreadable("the file is not a readable PDF") from error
    return DocumentText(text, len(reader.pages))


def read_first_page_text(pdf: bytes) -> str:
    try:
        reader = _opened(pdf)
        return (reader.pages[0].extract_text() or "").strip() if reader.pages else ""
    except PdfReadError as error:
        raise DocumentUnreadable("the file is not a readable PDF") from error


def _opened(pdf: bytes) -> PdfReader:
    reader = PdfReader(BytesIO(pdf))
    if reader.is_encrypted:
        raise DocumentUnreadable("the PDF is password protected")
    return reader
