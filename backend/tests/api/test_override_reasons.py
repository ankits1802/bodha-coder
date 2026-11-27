import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.db import SessionFactory
from app.models import CodeSet, Decision
from tests.api.review_helpers import KEEP_I10, access_rows, approve, decide, keep_i10_with_reason, note_detail
from tests.builders import DOCUMENTED, reviewed_note

PAYER = {"reason": "payer_policy", "note": "Plan pays I10 here"}


async def test_approval_is_refused_while_a_departing_choice_has_no_reason(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    assert (await decide(harness, practice, note_id, KEEP_I10)).status_code == 200

    refused = await approve(harness, practice, note_id)

    assert refused.status_code == 409
    body = refused.json()
    assert set(body) == {"error", "message"} and body["error"] == "conflict"
    assert body["message"].endswith(": dx:I10")
    finding = next(
        item for item in (await note_detail(harness, practice, note_id))["findings"] if item["key"] == "dx:I10"
    )
    assert (finding["choice"], finding["override"], finding["override_needed"]) == ("keep", None, True)
    assert finding["departing_choices"] == ["keep"]


async def test_a_reason_added_later_is_a_new_record_and_lets_the_note_be_approved(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await decide(harness, practice, note_id, KEEP_I10)

    reasoned = await decide(harness, practice, note_id, {**KEEP_I10, "reasons": {"dx:I10": PAYER}})

    assert reasoned.status_code == 200, reasoned.text
    decisions = [d for d in reasoned.json()["history"]["decisions"] if d["key"] == "dx:I10"]
    assert [(d["choice"], d["override_reason"], d["override_note"], d["role"]) for d in decisions] == [
        ("keep", None, None, "admin"),
        ("keep", "payer_policy", "Plan pays I10 here", "admin"),
    ]
    assert (await approve(harness, practice, note_id)).status_code == 200
    rows = [row for row in await access_rows(harness, practice) if row["action"] == "override reason"]
    assert [row["detail"] for row in rows] == ["dx:I10 · keep · Payer policy: Plan pays I10 here"]
    assert rows[0]["ip"] == "127.0.0.1"


@pytest.mark.parametrize(
    ("choices", "reasons"),
    [
        ({"dx:I10": "accept"}, {"dx:I10": DOCUMENTED}),
        ({"dx:I10": "keep"}, {"dx:I10": {"reason": "other", "note": " "}}),
        ({"dx:I10": "keep"}, {"dx:I10": {"reason": "documentation", "note": "x" * 501}}),
        ({"dx:I10": "keep"}, {"em": DOCUMENTED}),
        ({"dx:I10": "keep"}, {"dx:I10": {"reason": "gut feeling", "note": None}}),
    ],
)
async def test_a_reason_must_be_valid_and_belong_to_a_departing_choice(harness, icd_catalog, choices, reasons):
    practice, note_id = await reviewed_note(harness, icd_catalog)

    refused = await decide(harness, practice, note_id, {"choices": choices, "reasons": reasons})

    assert refused.status_code == 422, refused.text


async def test_editing_billed_codes_needs_a_reason_that_stays_on_the_code_set(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    path = f"/api/notes/{note_id}/billed-codes"
    codes = "99214, I12.9, E11.65, N18.30, R20.2"

    assert (await harness.client.put(path, headers=practice.admin, json={"codes": codes})).status_code == 422
    edited = await harness.client.put(path, headers=practice.admin, json={"codes": codes, "reason": PAYER})

    assert edited.status_code == 200, edited.text
    revisions = [(c["revision"], c["override_reason"], c["role"]) for c in edited.json()["history"]["code_sets"]]
    assert revisions == [(1, None, None), (2, "payer_policy", "admin")]
    edits = [row["detail"] for row in await access_rows(harness, practice) if row["action"] == "edited billed codes"]
    assert edits == [f"{codes} · Payer policy: Plan pays I10 here"]


async def test_hand_linked_pointers_need_a_reason_stored_on_each_line(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    path = f"/api/notes/{note_id}/pointers"
    lines = [{"code": "99214", "pointers": ["I12.9", "E11.65"]}]

    assert (await harness.client.put(path, headers=practice.admin, json={"lines": lines})).status_code == 422
    linked = await harness.client.put(path, headers=practice.admin, json={"lines": lines, "reason": DOCUMENTED})

    assert linked.status_code == 200, linked.text
    async with SessionFactory() as db:
        rows = (await db.scalars(select(Decision).where(Decision.suggestion_key.startswith("pointers:")))).all()
    assert [(row.override_reason, row.actor_role) for row in rows] == [("documentation", "admin")]


async def test_the_database_refuses_other_without_a_note(harness, icd_catalog):
    _, note_id = await reviewed_note(harness, icd_catalog)
    async with SessionFactory() as db:
        billed = await db.scalar(select(CodeSet).where(CodeSet.note_id == note_id))
        db.add(
            CodeSet(
                note_id=note_id, kind="billed", revision=9, codes=billed.codes, reason="edited", override_reason="other"
            )
        )
        with pytest.raises(IntegrityError):
            await db.commit()


async def test_the_reasoned_decision_reaches_the_approval_record(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await keep_i10_with_reason(harness, practice, note_id)
    assert (await approve(harness, practice, note_id)).status_code == 200

    detail = await note_detail(harness, practice, note_id)

    assert [snapshot["decisions"] for snapshot in detail["history"]["snapshots"]] == [1]
