from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select

from app.ai.contracts import (
    DiagnosisFinding,
    EmReview,
    ModelClient,
    PatientFacts,
    ReviewInputs,
    ReviewOutcome,
    ReviewReport,
)
from app.core.db import SessionFactory
from app.models import AuditRun, AuditSample, Note, User, utcnow
from tests.builders import DOCUMENTED, Harness, Practice, read_next_note, upload_note
from tests.fakes import NOTE_TEXT

SERVICE_DAY = "2026-11-25"
CODER_EMAIL = "coder@lakeside.example.com"


@dataclass
class SequenceReviewer:
    reports: list[ReviewReport]
    calls: list[ReviewInputs] = field(default_factory=list)

    async def __call__(self, client: ModelClient, inputs: ReviewInputs) -> ReviewOutcome:
        report = self.reports[len(self.calls) % len(self.reports)]
        self.calls.append(inputs)
        return ReviewOutcome(report=report, prompt_version="test")


def matching_report() -> ReviewReport:
    return ReviewReport(
        patient=PatientFacts(name="Marisol Reyes", age=67, sex="female"),
        em=EmReview(code="99215", mdm_level="High", justification="High decision-making.", evidence=["A1c 8.4"]),
        diagnoses=[
            DiagnosisFinding(name="Hypertension", icd10="I10", status="supported", evidence=["Hypertension"]),
            DiagnosisFinding(name="Type 2 diabetes", icd10="E11.9", status="supported", evidence=["type 2 diabetes"]),
            DiagnosisFinding(name="CKD stage 3", icd10="N18.30", status="supported", evidence=["CKD, stable"]),
        ],
    )


def higher_report() -> ReviewReport:
    return ReviewReport(
        em=EmReview(code="99215", mdm_level="High", justification="High decision-making."),
        diagnoses=[DiagnosisFinding(name="Hypertension", icd10="I10", status="supported")],
    )


async def read_note(harness: Harness, practice: Practice, icd_catalog, index: int, report=None) -> str:
    upload = await upload_note(
        harness,
        practice,
        file_name=f"{SERVICE_DAY} - REYES MARISOL - 99215 - Visit {index}.pdf",
        body=f"{NOTE_TEXT} Visit {index}.",
    )
    assert upload.status_code == 200, upload.text
    await read_next_note(harness, icd_catalog, report)
    listing = await harness.client.get(f"/api/notes?batch_id={upload.json()['batch_id']}", headers=practice.admin)
    return listing.json()["items"][0]["id"]


async def approved_note(harness: Harness, practice: Practice, icd_catalog, index: int, choices=None) -> str:
    note_id = await read_note(harness, practice, icd_catalog, index)
    if choices:
        decided = await harness.client.put(
            f"/api/notes/{note_id}/decisions",
            headers=practice.admin,
            json={
                "choices": choices,
                "reasons": {key: DOCUMENTED for key, value in choices.items() if value == "keep"},
            },
        )
        assert decided.status_code == 200, decided.text
    approved = await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)
    assert approved.status_code == 200, approved.text
    return note_id


async def note_of_item(item_id: str) -> str:
    async with SessionFactory() as db:
        return (await db.get_one(AuditSample, item_id)).note_id


async def user_id(email: str) -> str:
    async with SessionFactory() as db:
        return await db.scalar(select(User.id).where(User.email == email))


async def seed_audit(note_id: str, reviewer_id: str, outcomes: list[str], *, done: bool = True) -> str:
    finished = utcnow()
    status = "done" if done else "open"
    async with SessionFactory() as db:
        note = await db.get_one(Note, note_id)
        run = AuditRun(
            practice_id=note.practice_id,
            created_by=reviewer_id,
            purpose="audit",
            scope="practice",
            requested=len(outcomes),
            status=status,
        )
        db.add(run)
        await db.flush()
        for position, direction in enumerate(outcomes):
            db.add(
                AuditSample(
                    practice_id=note.practice_id,
                    note_id=note_id,
                    reviewer_id=reviewer_id,
                    run_id=run.id,
                    purpose="audit",
                    status=status,
                    answer={},
                    result={
                        "position": position,
                        "bodha": {"em": {"match": direction == "match", "direction": direction}},
                    },
                    completed_at=finished if done else None,
                )
            )
        await db.commit()
        return run.id
