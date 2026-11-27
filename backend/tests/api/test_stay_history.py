import json
from datetime import date

from sqlalchemy import select, update

from app.ai.contracts import PatientFacts
from app.core.db import SessionFactory
from app.models import Note
from tests.builders import marisol_report, practice_with_provider, read_next_note, upload_note
from tests.fakes import NOTE_TEXT, text_pdf

REPEATED = {"rule": "initial_visit_repeated", "severity": "denial", "codes": ["99305"], "earlier": "2026-11-02"}


async def nursing_note(harness, practice, day: str, billed: str, *, patient: str = "REYES MARISOL") -> str:
    cpt = billed.split(",")[0]
    pdf = (f"{day} - {patient} - {cpt} - Visit.pdf", text_pdf(f"Visit {day} {billed}"), "application/pdf")
    upload = await harness.client.post(
        "/api/uploads",
        headers=practice.admin,
        data={
            "provider_id": practice.provider_id,
            "service_date": day,
            "place_code": "31",
            "visit_type": "Nursing facility",
            "details": json.dumps([{"billed": billed}]),
        },
        files=[("files", pdf)],
    )
    assert upload.status_code == 200, upload.text
    async with SessionFactory() as db:
        return await db.scalar(select(Note.id).where(Note.batch_id == upload.json()["batch_id"]))


async def payer_flags(harness, practice, note_id: str) -> list[dict]:
    checks = await harness.client.get(f"/api/notes/{note_id}/claim-checks", headers=practice.admin)
    assert checks.status_code == 200, checks.text
    return checks.json()["payer_flags"]


async def born(note_id: str, day: date) -> None:
    async with SessionFactory() as db:
        await db.execute(update(Note).where(Note.id == note_id).values(patient_birth_date=day))
        await db.commit()


async def test_a_second_initial_visit_for_the_same_resident_names_the_first(harness):
    practice = await practice_with_provider(harness)
    admitted = await nursing_note(harness, practice, "2026-11-02", "99306, I10")
    repeated = await nursing_note(harness, practice, "2026-11-20", "99305, I10")
    stranger = await nursing_note(harness, practice, "2026-11-21", "99304, I10", patient="DOE JANE")

    assert await payer_flags(harness, practice, admitted) == []
    assert await payer_flags(harness, practice, repeated) == [REPEATED]
    assert await payer_flags(harness, practice, stranger) == []

    await born(admitted, date(1958, 3, 14))
    await born(repeated, date(1958, 3, 15))
    assert await payer_flags(harness, practice, repeated) == []
    await born(repeated, date(1958, 3, 14))
    assert await payer_flags(harness, practice, repeated) == [REPEATED]


async def test_a_discharge_between_the_visits_starts_a_new_stay(harness):
    practice = await practice_with_provider(harness)
    await nursing_note(harness, practice, "2026-11-02", "99306, I10")
    repeated = await nursing_note(harness, practice, "2026-11-20", "99305, I10")
    await nursing_note(harness, practice, "2026-11-10", "99316, I10")

    assert await payer_flags(harness, practice, repeated) == []


async def read_with_birth_date(harness, icd_catalog, practice, index: int, birth_date: date) -> date | None:
    name = f"2026-11-25 - REYES MARISOL - 99215 - Visit {index}.pdf"
    upload = await upload_note(harness, practice, file_name=name, body=f"{NOTE_TEXT} {index}")
    assert upload.status_code == 200, upload.text
    patient = PatientFacts(name="Marisol Reyes", age=67, sex="female", birth_date=birth_date)
    await read_next_note(harness, icd_catalog, marisol_report().model_copy(update={"patient": patient}))
    async with SessionFactory() as db:
        return await db.scalar(select(Note.patient_birth_date).where(Note.batch_id == upload.json()["batch_id"]))


async def test_a_stated_birth_date_is_kept_on_the_note_unless_it_follows_the_visit(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    assert await read_with_birth_date(harness, icd_catalog, practice, 1, date(1959, 3, 14)) == date(1959, 3, 14)
    assert await read_with_birth_date(harness, icd_catalog, practice, 2, date(2026, 12, 1)) is None
