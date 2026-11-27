from __future__ import annotations

from httpx import Response
from sqlalchemy import select

from app.ai.audit import AuditChecklistOutput, RiskArea
from app.ai.contracts import DiagnosisFinding, EmReview, PatientFacts, ReviewReport
from app.core.db import SessionFactory
from app.models import NoteReturn
from tests.builders import (
    Harness,
    Practice,
    invite_member,
    practice_with_provider,
    read_next_note,
    sign_in,
    upload_note,
)

FLAG = "Exam text copied from the last visit"
RETURN = {"reason": "level_not_supported", "note": "Exam repeated from the last visit"}
COMPLIANCE = {"name": "Jordan Diaz", "email": "jordan@lakeside.example.com", "role": "compliance"}
CODER = {"name": "Priya Nair", "email": "priya@lakeside.example.com", "role": "coder"}


def matching_report_with_critical_risk() -> ReviewReport:
    supported = [
        DiagnosisFinding(name="Hypertension", icd10="I10", status="supported", evidence=["BP 150/92"]),
        DiagnosisFinding(name="Type 2 diabetes", icd10="E11.9", status="supported", evidence=["A1c 7.1"]),
        DiagnosisFinding(name="CKD stage 3", icd10="N18.30", status="supported", evidence=["eGFR 48"]),
    ]
    audit = AuditChecklistOutput(
        requiredElements=[],
        codingCompliance=[],
        cmsCDICompliance=[],
        riskAreas=[RiskArea(id="risk-cloned", risk="Exam cloned from the last visit", severity="Critical")],
        overallComplianceScore=40,
        auditSummary="Cloned exam.",
    )
    return ReviewReport(
        patient=PatientFacts(name="Marisol Reyes", age=67, sex="female"),
        em=EmReview(code="99215", mdm_level="High", justification="High decision-making.", evidence=["BP 150/92"]),
        diagnoses=supported,
        audit=audit,
    )


async def note_at_risk(harness: Harness, icd_catalog) -> tuple[Practice, str]:
    practice = await practice_with_provider(harness)
    upload = await upload_note(harness, practice)
    assert upload.status_code == 200, upload.text
    await read_next_note(harness, icd_catalog, matching_report_with_critical_risk())
    listing = await harness.client.get("/api/notes", headers=practice.admin)
    return practice, listing.json()["items"][0]["id"]


async def compliance_member(harness: Harness, practice: Practice) -> dict[str, str]:
    await invite_member(harness, practice, **COMPLIANCE)
    return await sign_in(harness.client, COMPLIANCE["email"], secret_box=practice.secrets)


async def flag(harness: Harness, headers: dict[str, str], note_id: str) -> None:
    flagged = await harness.client.post(f"/api/notes/{note_id}/flag", headers=headers, json={"reason": FLAG})
    assert flagged.status_code == 200, flagged.text


async def send_back(harness: Harness, headers: dict[str, str], note_id: str, reason: dict | None = RETURN) -> Response:
    body = {"decision": "return", "return_reason": reason} if reason else {"decision": "return", "reason": FLAG}
    return await harness.client.post(f"/api/notes/{note_id}/compliance", headers=headers, json=body)


async def stored_returns(note_id: str) -> list[NoteReturn]:
    async with SessionFactory() as db:
        query = select(NoteReturn).where(NoteReturn.note_id == note_id).order_by(NoteReturn.created_at)
        return list((await db.scalars(query)).all())


async def decide_again(harness: Harness, practice: Practice, detail: dict) -> Response:
    choices = {item["key"]: item["allowed"][0] for item in detail["findings"] if item["decide_again"]}
    note_id = detail["note"]["id"]
    return await harness.client.put(
        f"/api/notes/{note_id}/decisions", headers=practice.admin, json={"choices": choices}
    )
