import pytest
from sqlalchemy import select

from app.core.db import SessionFactory
from app.core.errors import Conflict
from app.models import AccessLog, ApprovedClaim, CodeSet, Note, Provider
from app.services import auto_approval
from app.services.auto_approval import auto_approve, auto_approve_eligible, held_for_quality_check
from app.services.autonomy import provider_eligibility
from tests.api.quality_helpers import matching_report, read_note, seed_audit, user_id
from tests.builders import practice_with_provider

ADMIN_EMAIL = "admin@lakeside.example.com"


async def eligibility_of(note_id: str):
    async with SessionFactory() as db:
        note = await db.get_one(Note, note_id)
        return await provider_eligibility(db, await db.get_one(Provider, note.provider_id))


async def eligibility_after(outcomes: list[str], note_id: str, reviewer_id: str):
    await seed_audit(note_id, reviewer_id, outcomes)
    return await eligibility_of(note_id)


async def matching_note(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    note_id = await read_note(harness, practice, icd_catalog, 1, matching_report())
    return practice, note_id, await user_id(ADMIN_EMAIL)


def test_one_note_in_ten_is_held_for_a_person_by_its_id():
    assert [name for name in (f"note-{index}" for index in range(1, 21)) if held_for_quality_check(name)] == [
        "note-2",
        "note-12",
    ]
    assert sum(held_for_quality_check(f"note-{index}") for index in range(1000)) == 103


@pytest.mark.parametrize(
    ("outcomes", "reason", "low"),
    [
        (["match"] * 29, "too_few_notes", 0.88303),
        (["match"] * 30, "agreement_low", 0.886487),
        (["match"] * 35, "eligible", 0.901099),
        (["match"] * 143 + ["lower"] * 7, "eligible", 0.906814),
        (["match"] * 142 + ["higher"] * 8, "agreement_low", 0.898296),
        (["match"] * 284 + ["higher"] * 16, "too_many_higher", 0.915131),
    ],
)
async def test_autonomy_needs_thirty_notes_a_ninety_percent_lower_bound_and_few_higher_codes(
    harness, icd_catalog, outcomes, reason, low
):
    _, note_id, reviewer_id = await matching_note(harness, icd_catalog)
    eligibility = await eligibility_after(outcomes, note_id, reviewer_id)
    assert (eligibility.reason, eligibility.notes) == (reason, len(outcomes))
    assert eligibility.em_low == pytest.approx(low, abs=1e-6)


async def test_only_the_latest_completed_audit_counts(harness, icd_catalog):
    _, note_id, reviewer_id = await matching_note(harness, icd_catalog)
    assert (await eligibility_after(["match"] * 35, note_id, reviewer_id)).reason == "eligible"
    await seed_audit(note_id, reviewer_id, ["higher"] * 50, done=False)
    assert (await eligibility_of(note_id)).reason == "eligible"
    assert (await eligibility_after(["match"] * 31, note_id, reviewer_id)).reason == "agreement_low"


async def test_the_switch_turns_on_only_for_an_eligible_provider(harness, icd_catalog):
    practice, note_id, reviewer_id = await matching_note(harness, icd_catalog)
    path = f"/api/quality/providers/{practice.provider_id}/auto-approve"
    refused = await harness.client.put(path, headers=practice.admin, json={"on": True})
    assert (refused.status_code, refused.json()["message"]) == (
        409,
        "complete a blind audit of this provider's notes first",
    )
    listed = (await harness.client.get("/api/quality/providers", headers=practice.admin)).json()["items"]
    assert [(row["name"], row["auto_approve"], row["eligibility"]["reason"]) for row in listed] == [
        ("Elena Varga", False, "no_audit")
    ]

    await seed_audit(note_id, reviewer_id, ["match"] * 35)
    switched = await harness.client.put(path, headers=practice.admin, json={"on": True})
    assert (switched.status_code, switched.json()["auto_approve"]) == (200, True)
    assert (await harness.client.put(path, headers=practice.admin, json={"on": False})).json()["auto_approve"] is False


async def test_an_eligible_matching_note_is_approved_by_bodha_and_logged(harness, icd_catalog, monkeypatch):
    practice, note_id, reviewer_id = await matching_note(harness, icd_catalog)
    await seed_audit(note_id, reviewer_id, ["match"] * 35)
    await harness.client.put(
        f"/api/quality/providers/{practice.provider_id}/auto-approve", headers=practice.admin, json={"on": True}
    )
    monkeypatch.setattr(auto_approval, "held_for_quality_check", lambda note_id: True)
    async with SessionFactory() as db:
        note = await db.get_one(Note, note_id)
        assert (note.lane, note.lane_reason) == ("approve", "matches")
        assert await auto_approve_eligible(db, note) is False
        with pytest.raises(Conflict):
            await auto_approve(db, note)

    monkeypatch.setattr(auto_approval, "held_for_quality_check", lambda note_id: False)
    async with SessionFactory() as db:
        note = await db.get_one(Note, note_id)
        assert await auto_approve_eligible(db, note) is True
        await auto_approve(db, note)
        await db.commit()

    async with SessionFactory() as db:
        note = await db.get_one(Note, note_id)
        final = await db.scalar(select(CodeSet).where(CodeSet.note_id == note_id, CodeSet.kind == "final"))
        logged = await db.scalar(select(AccessLog).where(AccessLog.note_id == note_id, AccessLog.action == "approved"))
    assert (note.status, note.approved_by) == ("approved", None)
    assert (final.reason, final.actor_id, [code["code"] for code in final.codes]) == (
        "auto",
        None,
        ["99215", "I10", "E11.9", "N18.30"],
    )
    assert (logged.actor_name, logged.detail) == ("Bodha (auto)", "99215, I10, E11.9, N18.30 · snapshot 1")
    async with SessionFactory() as db:
        snapshot = await db.scalar(select(ApprovedClaim).where(ApprovedClaim.note_id == note_id))
    assert (snapshot.approved_by, snapshot.approver_name, snapshot.approver_role) == (None, "Bodha (auto)", "system")
    assert [code["code"] for code in snapshot.content["codes"]] == ["99215", "I10", "E11.9", "N18.30"]


async def test_a_flagged_or_switched_off_note_waits_for_a_person(harness, icd_catalog, monkeypatch):
    practice, note_id, reviewer_id = await matching_note(harness, icd_catalog)
    await seed_audit(note_id, reviewer_id, ["match"] * 35)
    monkeypatch.setattr(auto_approval, "held_for_quality_check", lambda note_id: False)
    async with SessionFactory() as db:
        assert await auto_approve_eligible(db, await db.get_one(Note, note_id)) is False

    await harness.client.put(
        f"/api/quality/providers/{practice.provider_id}/auto-approve", headers=practice.admin, json={"on": True}
    )
    async with SessionFactory() as db:
        assert await auto_approve_eligible(db, await db.get_one(Note, note_id)) is True
    flagged = await harness.client.post(f"/api/notes/{note_id}/flag", headers=practice.admin, json={"reason": "check"})
    assert flagged.status_code == 200, flagged.text
    async with SessionFactory() as db:
        assert await auto_approve_eligible(db, await db.get_one(Note, note_id)) is False
