from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from app.adapters.demo_answers import DemoOutcome
from app.adapters.demo_model import demo_outcome
from app.adapters.pdf_text import read_pdf_text
from tests.e2e_seed.api import Api, Caller, SeedFailed
from tests.e2e_seed.practices import Provider
from tests.fakes import text_pdf

__all__ = ["BILLED", "SERVICE_DAY", "SyntheticNote", "note_pdf", "upload_notes", "write_pdfs"]

SERVICE_DAY = date(2026, 11, 25)
BILLED = "99214, E11.65, I10"
PLACE = "11"
VISIT_TYPE = "Established patient"
MAX_VARIANTS = 400
READ_SECONDS = 120.0
POLL_SECONDS = 0.5
OUTCOME_LANES: dict[DemoOutcome, str] = {
    "matches": "approve",
    "billed_too_high": "coder",
    "billed_too_low": "coder",
    "cdi_query": "provider",
    "audit_risk": "compliance",
}
FINISHED = {"ready", "failed"}


@dataclass(frozen=True)
class SyntheticNote:
    first: str
    last: str
    outcome: DemoOutcome
    provider: Provider

    @property
    def patient(self) -> str:
        return f"{self.first} {self.last}"

    @property
    def file_name(self) -> str:
        billed = BILLED.split(",")[0]
        return f"{SERVICE_DAY.isoformat()} - {self.first.upper()} {self.last.upper()} - {billed} - Progress.pdf"

    def text(self, weeks: int) -> str:
        return (
            f"Patient: {self.patient}   DOB: 03/14/1959   Sex: Female   "
            f"Date of service: {SERVICE_DAY.strftime('%m/%d/%Y')}   Place of service: {PLACE}   "
            f"Provider: {self.provider.name}, MD   NPI: {self.provider.npi}   "
            "Synthetic test note. 67-year-old woman seen for follow-up of type 2 diabetes and hypertension. "
            "A1c 8.4. Assessment and plan: type 2 diabetes with hyperglycemia, increase metformin. "
            "Hypertension above goal, add amlodipine. "
            f"Return in {weeks} weeks. Electronically signed: {self.provider.name}, MD"
        )


def note_pdf(note: SyntheticNote) -> bytes:
    for weeks in range(1, MAX_VARIANTS):
        pdf = text_pdf(note.text(weeks))
        if demo_outcome(read_pdf_text(pdf).text.encode()) == note.outcome:
            return pdf
    raise SeedFailed(f"no synthetic note reads as {note.outcome}")


def write_pdfs(folder: Path, notes: list[SyntheticNote]) -> list[str]:
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for note in notes:
        path = folder / note.file_name
        path.write_bytes(note_pdf(note))
        paths.append(str(path))
    return paths


async def upload_notes(api: Api, caller: Caller, notes: list[SyntheticNote]) -> dict[str, str]:
    providers = {note.provider.id for note in notes}
    if len(providers) != 1:
        raise SeedFailed("upload the notes of one provider at a time")
    files = [("files", (note.file_name, note_pdf(note), "application/pdf")) for note in notes]
    data = {
        "provider_id": providers.pop(),
        "service_date": SERVICE_DAY.isoformat(),
        "place_code": PLACE,
        "visit_type": VISIT_TYPE,
        "details": json.dumps([{"billed": BILLED} for _ in notes]),
    }
    result = await api.send(caller, "POST", "/api/uploads", data=data, files=files)
    rows = await _read(api, caller, result["batch_ids"], len(notes))
    by_file = {row["file_name"]: row for row in rows}
    for note in notes:
        _check_lane(note, by_file.get(note.file_name))
    return {note.patient: by_file[note.file_name]["id"] for note in notes}


async def _read(api: Api, caller: Caller, batch_ids: list[str], expected: int) -> list[dict[str, Any]]:
    deadline = time.monotonic() + READ_SECONDS
    while time.monotonic() < deadline:
        rows = [row for batch in batch_ids for row in await _batch_rows(api, caller, batch)]
        if len(rows) == expected and all(row["status"] in FINISHED for row in rows):
            return rows
        await asyncio.sleep(POLL_SECONDS)
    raise SeedFailed(f"the worker did not read {expected} synthetic notes within {READ_SECONDS:.0f} seconds")


async def _batch_rows(api: Api, caller: Caller, batch_id: str) -> list[dict[str, Any]]:
    page = await api.send(caller, "GET", "/api/notes", params={"batch_id": batch_id})
    return page["items"]


def _check_lane(note: SyntheticNote, row: dict[str, Any] | None) -> None:
    if row is None or row["status"] != "ready" or row["lane"] != OUTCOME_LANES[note.outcome]:
        found = (row or {}).get("status"), (row or {}).get("lane")
        raise SeedFailed(f"{note.file_name} should be ready in {OUTCOME_LANES[note.outcome]}, found {found}")
