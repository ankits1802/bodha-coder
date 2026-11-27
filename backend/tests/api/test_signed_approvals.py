import base64
import hashlib
import json

import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError

from app.adapters.development_signer import DEVELOPMENT_KEY_ID, DevelopmentRecordSigner
from app.core.db import SessionFactory, permit_record_erasure
from app.models import ApprovedClaim, Note, Signature, SigningEvent
from app.services.approval import SIGNED_STATEMENTS
from tests.api.review_helpers import approve
from tests.builders import adopt_signature, invite_member, reviewed_note, sign_in

CODER = "cora@lakeside.example.com"


async def _events() -> list[SigningEvent]:
    async with SessionFactory() as db:
        return list((await db.scalars(select(SigningEvent).order_by(SigningEvent.signed_at))).all())


async def _approved(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    assert (await approve(harness, practice, note_id)).status_code == 200, "approval refused"
    [event] = await _events()
    return practice, note_id, event


async def _verify(harness, code: str) -> dict:
    response = await harness.client.get(f"/api/verify/{code}")
    assert response.status_code == 200, response.text
    return response.json()


async def test_a_person_without_a_signature_is_asked_for_one_and_nothing_is_approved(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await invite_member(harness, practice, name="Cora Coder", email=CODER, role="coder")
    coder = await sign_in(harness.client, CODER, secret_box=practice.secrets)

    refused = await harness.client.post(f"/api/notes/{note_id}/approve", headers=coder)
    bulk = await harness.client.post("/api/notes/approve", headers=coder, json={"note_ids": [note_id]})

    assert (refused.status_code, refused.json()["error"]) == (409, "signature_required")
    assert (bulk.status_code, bulk.json()["error"]) == (409, "signature_required")
    async with SessionFactory() as db:
        assert (await db.get_one(Note, note_id)).status == "ready"
        assert (await db.scalars(select(ApprovedClaim))).all() == []
    assert await _events() == []
    await adopt_signature(harness.client, coder, name="Cora Coder")
    assert (await harness.client.post(f"/api/notes/{note_id}/approve", headers=coder)).json() == {"status": "approved"}


async def test_approving_applies_the_signature_and_seals_the_frozen_claim(harness, icd_catalog):
    practice, note_id, event = await _approved(harness, icd_catalog)

    async with SessionFactory() as db:
        snapshot = await db.scalar(select(ApprovedClaim))
        note = await db.get_one(Note, note_id)
        signature = await db.get_one(Signature, event.signature_id)
    envelope = json.loads(event.envelope)
    assert (event.event, event.record_id, event.note_id, event.practice_id) == (
        "approval",
        snapshot.id,
        note_id,
        practice.id,
    )
    assert (event.signer_kind, event.signer_name, event.signer_title, event.typed_name) == (
        "user",
        "Practice Admin",
        "admin",
        "Practice Admin",
    )
    assert envelope["statement"] == SIGNED_STATEMENTS["approved"]
    assert envelope["document_sha256"] == note.file_sha256 == snapshot.document_sha256
    assert envelope["signature_sha256"] == signature.sha256
    assert (envelope["ip"], envelope["signer"]["id"]) == ("127.0.0.1", snapshot.approved_by)
    assert event.envelope_sha256 == hashlib.sha256(event.envelope.encode()).hexdigest()
    assert (event.seal_key_id, event.seal_algorithm) == (DEVELOPMENT_KEY_ID, "ECDSA_SHA_256")
    digest = hashlib.sha256(event.envelope.encode()).digest()
    assert await DevelopmentRecordSigner().verify_digest(
        digest, base64.b64decode(event.seal), key_id=DEVELOPMENT_KEY_ID
    )


async def test_the_verification_page_confirms_the_seal_with_no_patient_details(harness, icd_catalog):
    _, _, event = await _approved(harness, icd_catalog)

    answer = await _verify(harness, event.code.lower().replace("-", " "))

    assert answer == {
        "valid": True,
        "problems": [],
        "code": event.code,
        "event": "approval",
        "practice_name": "Lakeside",
        "signer_kind": "user",
        "signer_name": "Practice Admin",
        "signer_title": "admin",
        "signed_at": event.signed_at.isoformat(),
        "document_sha256": event.document_sha256,
        "envelope_sha256": event.envelope_sha256,
    }
    assert "Reyes" not in json.dumps(answer) and "Marisol" not in json.dumps(answer)


async def test_an_unknown_or_malformed_code_is_not_found(harness):
    assert (await harness.client.get("/api/verify/ABCD-EFGH-JKMN")).status_code == 404
    assert (await harness.client.get("/api/verify/not-a-code")).status_code == 404


async def test_verification_is_rate_limited_per_address(harness):
    answers = [(await harness.client.get("/api/verify/ABCD-EFGH-JKMN")).status_code for _ in range(31)]
    assert answers[:30] == [404] * 30 and answers[30] == 429


async def test_a_changed_signature_image_is_detected(harness, icd_catalog):
    _, _, event = await _approved(harness, icd_catalog)
    async with SessionFactory() as db:
        key = (await db.get_one(Signature, event.signature_id)).file_key
    harness.store.objects[key] = b"another image"

    assert (await _verify(harness, event.code))["problems"] == ["signature_changed"]


async def test_a_changed_frozen_claim_is_detected(harness, icd_catalog):
    _, _, event = await _approved(harness, icd_catalog)
    async with SessionFactory() as db:
        await db.execute(text("ALTER TABLE approved_claims DISABLE TRIGGER approved_claims_append_only"))
        await db.execute(update(ApprovedClaim).values(approver_name="Someone Else"))
        await db.execute(text("ALTER TABLE approved_claims ENABLE TRIGGER approved_claims_append_only"))
        await db.commit()

    answer = await _verify(harness, event.code)

    assert (answer["valid"], answer["problems"]) == (False, ["record_changed"])


async def test_a_changed_signing_record_breaks_the_envelope_and_the_seal(harness, icd_catalog):
    _, _, event = await _approved(harness, icd_catalog)
    async with SessionFactory() as db:
        await db.execute(text("ALTER TABLE signing_events DISABLE TRIGGER signing_events_sealed"))
        await db.execute(update(SigningEvent).values(signer_name="Someone Else"))
        await db.execute(text("ALTER TABLE signing_events ENABLE TRIGGER signing_events_sealed"))
        await db.commit()

    assert (await _verify(harness, event.code))["problems"] == ["envelope_changed", "seal_invalid"]


async def test_the_database_refuses_to_change_or_delete_sealed_rows(harness, icd_catalog):
    _, _, event = await _approved(harness, icd_catalog)
    for statement in (
        update(SigningEvent).values(statement="changed"),
        delete(SigningEvent),
        update(Signature).values(typed_name="changed"),
        delete(Signature),
    ):
        async with SessionFactory() as db:
            with pytest.raises(DBAPIError, match="sealed records"):
                await db.execute(statement)
    assert [row.id for row in await _events()] == [event.id]
    async with SessionFactory() as db:
        await permit_record_erasure(db)
        erased = await db.execute(delete(SigningEvent))
        await db.rollback()
    assert erased.rowcount == 1
    assert [row.id for row in await _events()] == [event.id]


async def test_deleting_an_approved_note_erases_its_seals_and_keeps_the_signer_s_signature(harness, icd_catalog):
    practice, note_id, event = await _approved(harness, icd_catalog)

    deleted = await harness.client.post("/api/notes/delete", headers=practice.admin, json={"note_ids": [note_id]})

    assert deleted.status_code == 200, deleted.text
    assert await _events() == []
    async with SessionFactory() as db:
        assert await db.get(Signature, event.signature_id) is not None


async def test_a_compliance_decision_is_sealed_as_its_own_event(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    flagged = await harness.client.post(f"/api/notes/{note_id}/flag", headers=practice.admin, json={"reason": "Copied"})
    assert flagged.status_code == 200, flagged.text
    await invite_member(harness, practice, name="Jordan Diaz", email="jordan@lakeside.example.com", role="compliance")
    compliance = await sign_in(harness.client, "jordan@lakeside.example.com", secret_box=practice.secrets)
    await adopt_signature(harness.client, compliance, name="Jordan Diaz")

    body = {"decision": "confirm", "reason": "Exam text reviewed"}
    confirmed = await harness.client.post(f"/api/notes/{note_id}/compliance", headers=compliance, json=body)

    assert confirmed.status_code == 200, confirmed.text
    [event] = await _events()
    assert (event.event, event.signer_name, event.signer_title) == ("compliance_decision", "Jordan Diaz", "compliance")
    assert event.statement == SIGNED_STATEMENTS["compliance confirm"]
    assert (await _verify(harness, event.code))["valid"] is True
