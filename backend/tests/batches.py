from __future__ import annotations

import io
import json
from dataclasses import dataclass
from datetime import date

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen.canvas import Canvas

from tests.builders import Harness, Practice

LINE_STEP = 14
TOP = 740


@dataclass(frozen=True)
class NoteFile:
    name: str
    pdf: bytes
    billed: str


def lines_pdf(lines: list[str]) -> bytes:
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=LETTER)
    for index, line in enumerate(lines):
        canvas.drawString(40, TOP - index * LINE_STEP, line)
    canvas.save()
    return buffer.getvalue()


async def add_provider(harness: Harness, practice: Practice, *, name: str, specialty: str | None) -> str:
    response = await harness.client.post(
        "/api/providers",
        headers=practice.admin,
        json={
            "name": name,
            "credential": "MD",
            "specialty": specialty,
            "place_code": "11",
            "email": f"{name.split()[-1].lower()}@clinic.example.com",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


async def upload_batch(
    harness: Harness, practice: Practice, provider_id: str, service_date: date, files: list[NoteFile]
) -> None:
    response = await harness.client.post(
        "/api/uploads",
        headers=practice.admin,
        data={
            "provider_id": provider_id,
            "service_date": service_date.isoformat(),
            "place_code": "11",
            "visit_type": "Established patient",
            "details": json.dumps([{"billed": item.billed} for item in files]),
        },
        files=[("files", (item.name, item.pdf, "application/pdf")) for item in files],
    )
    assert response.status_code == 200, response.text
    assert response.json()["accepted"] == [item.name for item in files]


async def note_ids_by_file(harness: Harness, practice: Practice) -> dict[str, str]:
    listing = await harness.client.get("/api/notes", headers=practice.admin)
    assert listing.status_code == 200, listing.text
    return {row["file_name"]: row["id"] for row in listing.json()["items"]}
