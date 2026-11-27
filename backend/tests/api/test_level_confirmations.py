from sqlalchemy import select

from app.core.db import SessionFactory
from app.models import AddendumRequest, ApprovedClaim, NoteText, ProviderAttestation
from app.services.attestations import LEVEL_ATTESTATION
from tests.api.review_helpers import (
    access_rows,
    approve,
    keep_i10_with_reason,
    note_detail,
    provider_session,
    turn_on_level_confirmation,
)
from tests.builders import invite_member, reviewed_note, sign_in

SHOWN = (
    "Visit of 25 Nov 2026\nBilled level: 99215\nApproved level: 99214\nEvidence from the note:\n“increase metformin”"
)


async def _approved_with_confirmation(harness, icd_catalog, *, hold: bool):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    assert (await turn_on_level_confirmation(harness, practice, hold=hold)).status_code == 200
    await keep_i10_with_reason(harness, practice, note_id)
    assert (await approve(harness, practice, note_id)).status_code == 200
    return practice, note_id, harness.messenger.last_fragment()


async def _attestations() -> list[ProviderAttestation]:
    async with SessionFactory() as db:
        return list((await db.scalars(select(ProviderAttestation).order_by(ProviderAttestation.created_at))).all())


async def test_the_setting_is_off_by_default_and_approval_then_asks_nobody(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    sent_before = len(harness.messenger.sent)
    await keep_i10_with_reason(harness, practice, note_id)

    assert (await approve(harness, practice, note_id)).status_code == 200

    assert len(harness.messenger.sent) == sent_before
    setup = (await harness.client.get("/api/practice/setup", headers=practice.admin)).json()
    assert setup["review"] == {"confirm_level_changes": False, "hold_until_confirmed": False}


async def test_only_admins_change_the_setting_and_hold_needs_confirmation(harness, icd_catalog):
    practice, _ = await reviewed_note(harness, icd_catalog)
    await invite_member(harness, practice, name="Cora Coder", email="cora@lakeside.example.com", role="coder")
    coder = await sign_in(harness.client, "cora@lakeside.example.com")
    body = {"confirm_level_changes": False, "hold_until_confirmed": True}

    refused = await harness.client.put("/api/practice/review-settings", headers=coder, json=body)
    saved = await harness.client.put("/api/practice/review-settings", headers=practice.admin, json=body)

    assert refused.status_code == 403
    assert saved.json() == {"confirm_level_changes": False, "hold_until_confirmed": False}


async def test_the_provider_sees_both_levels_and_the_evidence_and_confirms(harness, icd_catalog):
    practice, note_id, link = await _approved_with_confirmation(harness, icd_catalog, hold=False)
    assert "Patient" not in harness.messenger.sent[-1][1] and "Reyes" not in harness.messenger.sent[-1][1]
    provider = await provider_session(harness, link)

    shown = (await harness.client.get("/api/respond", headers=provider)).json()
    assert (shown["purpose"], shown["attestation"]) == ("level_change", LEVEL_ATTESTATION)
    assert shown["level_change"] == {"billed": "99215", "approved": "99214", "shown": SHOWN}
    answered = await harness.client.post(
        "/api/respond/level-change",
        headers=provider,
        json={"answer": "confirm", "confirmed": True, "attestation": LEVEL_ATTESTATION},
    )

    assert answered.json() == {"status": "answered", "answer": "confirm"}
    [statement] = await _attestations()
    async with SessionFactory() as db:
        texts = list((await db.scalars(select(NoteText.id).where(NoteText.note_id == note_id))).all())
        snapshot = await db.scalar(select(ApprovedClaim.id))
    assert (statement.purpose, statement.answer, statement.wording, statement.shown) == (
        "level_change",
        "confirm",
        LEVEL_ATTESTATION,
        SHOWN,
    )
    assert (statement.text_revision_ids, statement.approved_claim_id, statement.ip) == (texts, snapshot, "127.0.0.1")
    assert statement.user_agent.startswith("python-httpx")
    assert (await note_detail(harness, practice, note_id))["note"]["status"] == "approved"


async def test_a_disagreement_needs_a_comment_reopens_the_note_and_tells_the_approver(harness, icd_catalog):
    practice, note_id, link = await _approved_with_confirmation(harness, icd_catalog, hold=False)
    provider = await provider_session(harness, link)
    path = "/api/respond/level-change"

    bare = await harness.client.post(path, headers=provider, json={"answer": "disagree", "confirmed": True})
    disagreed = await harness.client.post(
        path, headers=provider, json={"answer": "disagree", "comment": "Time supports 99215.", "confirmed": True}
    )

    assert (bare.status_code, disagreed.status_code) == (422, 200)
    detail = await note_detail(harness, practice, note_id)
    assert detail["note"]["status"] == "ready"
    to, body = harness.messenger.sent[-1]
    assert to == "admin@lakeside.example.com"
    assert f"/notes/{note_id}" in body and "Lakeside" in body
    assert "Reyes" not in body and "Marisol" not in body and "99215" not in body
    assert [(row.answer, row.comment) for row in await _attestations()] == [("disagree", "Time supports 99215.")]
    actions = [row["action"] for row in await access_rows(harness, practice)]
    assert "disagreed with visit level" in actions and "reopened after disagreement" in actions


async def test_with_hold_on_the_claim_cannot_be_exported_until_the_provider_confirms(harness, icd_catalog):
    practice, note_id, link = await _approved_with_confirmation(harness, icd_catalog, hold=True)
    export = "/api/billing/export"

    [row] = (await harness.client.get("/api/billing", headers=practice.admin)).json()["items"]
    everything = await harness.client.post(export, headers=practice.admin, json={})
    named = await harness.client.post(export, headers=practice.admin, json={"note_ids": [note_id]})
    lines = await harness.client.post("/api/billing/claim-lines", headers=practice.admin, json={"note_ids": [note_id]})

    assert row["held"] is True
    assert (everything.status_code, named.status_code, lines.status_code) == (422, 409, 409)
    provider = await provider_session(harness, link)
    await harness.client.post(
        "/api/respond/level-change", headers=provider, json={"answer": "confirm", "confirmed": True}
    )
    assert (await harness.client.post(export, headers=practice.admin, json={})).status_code == 200


async def test_reopening_cancels_a_pending_confirmation(harness, icd_catalog):
    practice, note_id, _ = await _approved_with_confirmation(harness, icd_catalog, hold=True)

    assert (await harness.client.post(f"/api/notes/{note_id}/reopen", headers=practice.admin)).status_code == 200

    async with SessionFactory() as db:
        statuses = (await db.scalars(select(AddendumRequest.status))).all()
    assert list(statuses) == ["cancelled"]


async def test_code_checks_are_logged_with_address_and_never_the_code(harness, icd_catalog):
    practice, _, link = await _approved_with_confirmation(harness, icd_catalog, hold=False)

    await provider_session(harness, link, wrong_first=True)

    rows = [row for row in await access_rows(harness, practice) if row["actor_kind"] == "provider"]
    checks = [(row["action"], row["ip"], row["detail"]) for row in rows if "code" in row["action"]]
    assert checks == [("verified code", "127.0.0.1", None), ("code not accepted", "127.0.0.1", None)]
    assert all(row["user_agent"].startswith("python-httpx") for row in rows)
