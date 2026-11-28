import csv
import io

from sqlalchemy import update

from app.ai.contracts import DiagnosisFinding, EmReview, PatientFacts, ReviewReport
from app.codes.billing_codes import MAX_MODIFIERS
from app.core.db import SessionFactory
from app.models import Note
from app.services.claim_lines import CLAIM_LINE_COLUMNS
from tests.builders import DOCUMENTED, reviewed_note

HYPERTENSION = DiagnosisFinding(name="Hypertension", icd10="I10", status="supported", evidence=["Hypertension"])


def timed_visit(minutes: int) -> ReviewReport:
    return ReviewReport(
        patient=PatientFacts(name="Marisol Reyes", age=52, sex="female"),
        em=EmReview(
            code="99215",
            basis="Time",
            mdm_level="Moderate",
            time_minutes=minutes,
            justification=f"Total time {minutes} minutes.",
            evidence=[f"Total time on the date of the encounter: {minutes} minutes."],
        ),
        diagnoses=[HYPERTENSION],
    )


async def _bill(harness, practice, note_id: str, codes: str) -> None:
    edited = await harness.client.put(
        f"/api/notes/{note_id}/billed-codes", headers=practice.admin, json={"codes": codes, "reason": DOCUMENTED}
    )
    assert edited.status_code == 200, edited.text


async def _payer(harness, practice, note_id: str, plan_type: str) -> None:
    payer = await harness.client.post(
        "/api/practice/payers",
        headers=practice.admin,
        json={"name": "Medicare Part B", "payer_id": "MCRB", "plan_type": plan_type},
    )
    assert payer.status_code == 200, payer.text
    async with SessionFactory() as db:
        await db.execute(update(Note).where(Note.id == note_id).values(payer=payer.json()["id"]))
        await db.commit()


async def _flags(harness, practice, note_id: str) -> list[dict]:
    response = await harness.client.get(f"/api/notes/{note_id}/claim-checks", headers=practice.admin)
    assert response.status_code == 200, response.text
    return response.json()["payer_flags"]


async def test_a_commercial_claim_with_99417_by_time_is_approved_and_exported_with_its_units(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog, timed_visit(70))
    await _bill(harness, practice, note_id, "99215, 99417x2, I10")
    assert await _flags(harness, practice, note_id) == []

    approved = await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)
    assert approved.status_code == 200, approved.text

    exported = await harness.client.post("/api/billing/claim-lines", headers=practice.admin, json={"format": "json"})
    assert exported.status_code == 200, exported.text
    [claim] = exported.json()["claims"]
    assert claim["diagnoses"] == [{"pointer": "A", "code": "I10"}]
    assert claim["lines"] == [
        {"line": 1, "procedure": "99215", "modifiers": [], "units": 1, "pointers": ["A"]},
        {"line": 2, "procedure": "99417", "modifiers": [], "units": 2, "pointers": ["A"]},
    ]


async def test_the_claim_line_csv_carries_99417_with_its_units_and_its_primarys_pointer(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog, timed_visit(85))
    await _bill(harness, practice, note_id, "99215, 99417x3, I10")
    assert (await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)).status_code == 200

    response = await harness.client.post(
        "/api/billing/claim-lines", headers=practice.admin, json={"note_ids": [note_id], "format": "csv"}
    )

    assert response.status_code == 200, response.text
    header, *rows = list(csv.reader(io.StringIO(response.text)))
    assert tuple(header) == CLAIM_LINE_COLUMNS
    procedure, units, pointers = (header.index(name) for name in ("procedure", "units", "diagnosis_pointers"))
    assert [(row[procedure], row[units], row[pointers]) for row in rows] == [("99215", "1", "A"), ("99417", "3", "A")]
    assert all(row[header.index("diagnosis_a")] == "I10" for row in rows)
    assert all(row[header.index(f"modifier_{number}")] == "" for row in rows for number in range(1, MAX_MODIFIERS + 1))


async def test_a_billed_99417_the_time_does_not_reach_is_suggested_for_removal(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog, timed_visit(50))
    await _bill(harness, practice, note_id, "99215, 99417, I10")

    detail = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()

    item = next(item for item in detail["findings"] if item["key"] == "cpt:99417")
    assert (item["action"], item["code_before"], item["choice"]) == ("remove", "99417", "accept")
    assert detail["claim"] == ["99215", "I10"]


async def test_medicare_claims_are_told_to_use_g2212_instead_of_99417(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog, timed_visit(60))
    await _bill(harness, practice, note_id, "99215, 99417, I10")
    await _payer(harness, practice, note_id, "medicare")

    assert await _flags(harness, practice, note_id) == [
        {"rule": "prolonged_medicare", "severity": "denial", "codes": ["99417"]}
    ]


async def test_a_99417_kept_beside_a_99214_is_flagged_without_a_payer(harness, icd_catalog):
    report = ReviewReport(em=EmReview(code="99214", mdm_level="Moderate"), diagnoses=[HYPERTENSION])
    practice, note_id = await reviewed_note(harness, icd_catalog, report)
    await _bill(harness, practice, note_id, "99214, 99417, I10")
    assert await _flags(harness, practice, note_id) == []

    kept = await harness.client.put(
        f"/api/notes/{note_id}/decisions",
        headers=practice.admin,
        json={"choices": {"cpt:99417": "keep"}, "reasons": {"cpt:99417": DOCUMENTED}},
    )

    assert kept.status_code == 200, kept.text
    assert await _flags(harness, practice, note_id) == [
        {"rule": "prolonged_without_visit", "severity": "denial", "codes": ["99417"]}
    ]
