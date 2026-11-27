import json
from datetime import timedelta

from sqlalchemy import update

from app.ai.contracts import DiagnosisFinding, EmReview, PatientFacts, ReviewReport
from app.core.db import SessionFactory
from app.models import Note, utcnow
from tests.api.inbox_helpers import ask_provider
from tests.builders import BILLED, DOCUMENTED, Harness, Practice, practice_with_provider, read_next_note, reviewed_note
from tests.fakes import NOTE_TEXT, text_pdf

IMPACT_99215_TO_99214 = 13_561 - 19_239
MATCHING_LEVEL = "99214, I10, E11.9, N18.30"


def questions_report() -> ReviewReport:
    return ReviewReport(
        patient=PatientFacts(name="Jonah Pike", age=41, sex="male"),
        em=EmReview(code="99215", mdm_level="High", justification="High decision-making.", evidence=["A1c 8.4"]),
        diagnoses=[
            DiagnosisFinding(name="Hypertension", icd10="I10", status="supported", evidence=["Hypertension"]),
            DiagnosisFinding(name="Type 2 diabetes", icd10="E11.9", status="supported", evidence=["type 2 diabetes"]),
            DiagnosisFinding(
                name="CKD",
                icd10="N18.30",
                status="needs_specificity",
                evidence=["CKD, stable"],
                suggestion="Stage not documented",
            ),
        ],
    )


async def upload_on(harness: Harness, practice: Practice, *, name: str, day: str, billed: str) -> str:
    response = await harness.client.post(
        "/api/uploads",
        headers=practice.admin,
        data={
            "provider_id": practice.provider_id,
            "service_date": day,
            "place_code": "11",
            "visit_type": "Established patient",
            "details": json.dumps([{"billed": billed}]),
        },
        files=[("files", (name, text_pdf(f"{NOTE_TEXT} {name}"), "application/pdf"))],
    )
    assert response.status_code == 200, response.text
    listing = await harness.client.get(
        "/api/notes", headers=practice.admin, params={"batch_id": response.json()["batch_id"]}
    )
    return listing.json()["items"][0]["id"]


async def queue(harness: Harness, practice: Practice, **params) -> dict:
    response = await harness.client.get("/api/notes", headers=practice.admin, params=params)
    assert response.status_code == 200, response.text
    return response.json()


async def test_placement_stores_the_dollar_impact_of_the_suggested_claim_and_decisions_move_it(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    assert [row["impact_cents"] for row in (await queue(harness, practice))["items"]] == [IMPACT_99215_TO_99214]

    kept = await harness.client.put(
        f"/api/notes/{note_id}/decisions",
        headers=practice.admin,
        json={"choices": {"em": "keep"}, "reasons": {"em": DOCUMENTED}},
    )

    assert kept.status_code == 200, kept.text
    assert [row["impact_cents"] for row in (await queue(harness, practice))["items"]] == [0]


async def test_the_queue_sorts_by_due_date_or_by_dollar_impact_with_unknown_impact_last(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    higher = await upload_on(harness, practice, name="higher.pdf", day="2026-11-25", billed=BILLED)
    level = await upload_on(harness, practice, name="level.pdf", day="2026-11-20", billed=MATCHING_LEVEL)
    await read_next_note(harness, icd_catalog)
    await read_next_note(harness, icd_catalog)
    unread = await upload_on(harness, practice, name="unread.pdf", day="2026-11-18", billed=BILLED)

    by_due = await queue(harness, practice)
    by_impact = await queue(harness, practice, sort="impact")

    assert [row["id"] for row in by_due["items"]] == [unread, level, higher]
    assert [(row["id"], row["impact_cents"]) for row in by_impact["items"]] == [
        (higher, IMPACT_99215_TO_99214),
        (level, 0),
        (unread, None),
    ]
    assert (await harness.client.get("/api/notes", headers=practice.admin, params={"sort": "money"})).status_code == 422


async def test_the_provider_lane_is_split_into_questions_to_send_and_waiting_on_provider(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    waiting = await upload_on(harness, practice, name="waiting.pdf", day="2026-11-25", billed=BILLED)
    await read_next_note(harness, icd_catalog)
    await ask_provider(harness, practice.admin, waiting)
    questions = await upload_on(harness, practice, name="questions.pdf", day="2026-11-25", billed=BILLED)
    await read_next_note(harness, icd_catalog, questions_report())

    to_send = await queue(harness, practice, lane="provider", reason="questions")
    sent = await queue(harness, practice, lane="provider", reason="waiting_on_provider")
    today = (await harness.client.get("/api/today", headers=practice.admin)).json()

    assert [row["id"] for row in to_send["items"]] == [questions]
    assert [row["id"] for row in sent["items"]] == [waiting]
    for counts in (to_send["provider_reasons"], today["provider_reasons"]):
        assert (counts["questions"]["total"], counts["waiting_on_provider"]["total"]) == (1, 1)
    assert to_send["lanes"]["provider"]["total"] == 2


async def test_overdue_shows_only_open_notes_past_their_due_time(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    late = await upload_on(harness, practice, name="late.pdf", day="2026-11-25", billed=BILLED)
    early = await upload_on(harness, practice, name="early.pdf", day="2026-11-25", billed=BILLED)
    async with SessionFactory() as db:
        await db.execute(update(Note).where(Note.id == late).values(due_at=utcnow() - timedelta(hours=1)))
        await db.execute(update(Note).where(Note.id == early).values(due_at=utcnow() + timedelta(hours=30)))
        await db.commit()

    overdue = await queue(harness, practice, overdue="true")

    assert [row["id"] for row in overdue["items"]] == [late]
    assert overdue["all_total"] == 2
