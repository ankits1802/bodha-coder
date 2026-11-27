from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Literal
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Flowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

__all__ = [
    "PdfBlock",
    "PdfDocument",
    "PdfFacts",
    "PdfHeading",
    "PdfImage",
    "PdfPageBreak",
    "PdfTable",
    "PdfText",
    "UnreadableImage",
    "image_size",
    "render_pdf",
]

TextTone = Literal["body", "secondary", "quote", "label"]
FONT = "Helvetica"
BOLD = "Helvetica-Bold"
LABEL = colors.HexColor("#1D1D1F")
SECONDARY = colors.HexColor("#6E6E73")
SEPARATOR = colors.HexColor("#E5E5EA")
QUOTE_FILL = colors.HexColor("#F5F5F7")
MARGIN = 0.75 * inch
FOOTER_Y = 0.45 * inch
FRAME_WIDTH = LETTER[0] - 2 * MARGIN
FACT_LABEL_WIDTH = 1.9 * inch
IMAGE_WIDTH = 3 * inch
IMAGE_HEIGHT = 1.25 * inch


@dataclass(frozen=True)
class PdfHeading:
    text: str
    level: Literal[1, 2, 3] = 2


@dataclass(frozen=True)
class PdfText:
    text: str
    tone: TextTone = "body"


@dataclass(frozen=True)
class PdfFacts:
    rows: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class PdfTable:
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    weights: tuple[int, ...] = ()


@dataclass(frozen=True)
class PdfPageBreak:
    pass


@dataclass(frozen=True)
class PdfImage:
    data: bytes
    width: float = IMAGE_WIDTH
    height: float = IMAGE_HEIGHT


PdfBlock = PdfHeading | PdfText | PdfFacts | PdfTable | PdfImage | PdfPageBreak


class UnreadableImage(ValueError):
    pass


@dataclass(frozen=True)
class PdfDocument:
    title: str
    footer: str
    blocks: tuple[PdfBlock, ...]


STYLES = {
    1: ParagraphStyle("title", fontName=BOLD, fontSize=22, leading=27, textColor=LABEL, spaceAfter=14),
    2: ParagraphStyle(
        "section", fontName=BOLD, fontSize=14, leading=18, textColor=LABEL, spaceBefore=14, spaceAfter=6, keepWithNext=1
    ),
    3: ParagraphStyle(
        "item", fontName=BOLD, fontSize=11, leading=14, textColor=LABEL, spaceBefore=8, spaceAfter=3, keepWithNext=1
    ),
    "body": ParagraphStyle("body", fontName=FONT, fontSize=10, leading=13.5, textColor=LABEL, spaceAfter=4),
    "secondary": ParagraphStyle("secondary", fontName=FONT, fontSize=9, leading=12, textColor=SECONDARY, spaceAfter=4),
    "label": ParagraphStyle("label", fontName=BOLD, fontSize=9, leading=12, textColor=SECONDARY),
    "quote": ParagraphStyle(
        "quote",
        fontName=FONT,
        fontSize=10,
        leading=13.5,
        textColor=LABEL,
        leftIndent=10,
        borderPadding=(4, 6, 4, 6),
        backColor=QUOTE_FILL,
        spaceBefore=3,
        spaceAfter=7,
    ),
}


def render_pdf(document: PdfDocument) -> bytes:
    buffer = io.BytesIO()
    template = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=document.title,
        author="Bodha Assure",
        creator="Bodha Assure",
    )

    def footer(canvas: Canvas, _: SimpleDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont(FONT, 8)
        canvas.setFillColor(SECONDARY)
        canvas.drawString(MARGIN, FOOTER_Y, document.footer)
        canvas.drawRightString(LETTER[0] - MARGIN, FOOTER_Y, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    story = [flowable for block in document.blocks for flowable in _flowables(block)]
    template.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


def image_size(data: bytes) -> tuple[int, int]:
    try:
        reader = ImageReader(io.BytesIO(data))
        reader.getRGBData()
        width, height = reader.getSize()
    except (OSError, ValueError, SyntaxError) as error:
        raise UnreadableImage("the image cannot be read") from error
    return int(width), int(height)


def _image(block: PdfImage) -> Image:
    width, height = image_size(block.data)
    scale = min(block.width / width, block.height / height)
    return Image(io.BytesIO(block.data), width=width * scale, height=height * scale, hAlign="LEFT")


def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def _flowables(block: PdfBlock) -> list[Flowable]:
    if isinstance(block, PdfHeading):
        return [_paragraph(block.text, STYLES[block.level])]
    if isinstance(block, PdfText):
        return [_paragraph(block.text, STYLES[block.tone])]
    if isinstance(block, PdfFacts):
        rows = [[_paragraph(label, STYLES["label"]), _paragraph(value, STYLES["body"])] for label, value in block.rows]
        return [_table(rows, (FACT_LABEL_WIDTH, FRAME_WIDTH - FACT_LABEL_WIDTH), header=False), Spacer(1, 6)]
    if isinstance(block, PdfTable):
        header = [_paragraph(column, STYLES["label"]) for column in block.columns]
        body = [[_paragraph(cell, STYLES["body"]) for cell in row] for row in block.rows]
        return [_table([header, *body], _widths(block), header=True), Spacer(1, 6)]
    if isinstance(block, PdfImage):
        return [_image(block), Spacer(1, 6)]
    return [PageBreak()]


def _widths(block: PdfTable) -> tuple[float, ...]:
    weights = block.weights or (1,) * len(block.columns)
    if len(weights) != len(block.columns):
        raise ValueError(f"{len(block.columns)} columns but {len(weights)} weights")
    return tuple(FRAME_WIDTH * weight / sum(weights) for weight in weights)


def _table(rows: list[list[Paragraph]], widths: tuple[float, ...], *, header: bool) -> Table:
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, SEPARATOR),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    return Table(rows, colWidths=widths, hAlign="LEFT", repeatRows=1 if header else 0, style=TableStyle(commands))
