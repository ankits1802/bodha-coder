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
        reader = PdfReader(BytesIO(pdf))
        if reader.is_encrypted:
            raise DocumentUnreadable("the PDF is password protected")
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except PdfReadError as error:
        raise DocumentUnreadable("the file is not a readable PDF") from error
    return DocumentText(text, len(reader.pages))
