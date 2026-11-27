import json

from sqlalchemy import select

from app.core.db import SessionFactory
from app.models import Note, ProviderAttestation, Signature, SignatureAdoption, SigningEvent
from app.services.attestations import ADDENDUM_ATTESTATION, LEVEL_ATTESTATION
from tests.api.review_helpers import (
    approve,
    keep_i10_with_reason,
    provider_session,
    provider_signature,
    turn_on_level_confirmation,
)
from tests.builders import read_next_note, reviewed_note
from tests.fakes import signature_data_url, signature_png

QUESTION = {"key": "dx:N18.30", "text": "What stage is the kidney disease?"}
ANSWERS = [{"key": "dx:N18.30", "choice": "Yes"}]


async def _asked(harness, practice, note_id) -> dict[str, str]:
    asked = await harness.client.post(
        f"/api/notes/{note_id}/ask", headers=practice.admin, json={"questions": [QUESTION], "channel": "email"}
    )
    assert asked.status_code == 200, asked.text
    return await provider_session(harness, harness.messenger.last_fragment())


async def _events() -> list[SigningEvent]:
    async with SessionFactory() as db:
        return list((await db.scalars(select(SigningEvent).order_by(SigningEvent.signed_at))).all())


async def test_a_provider_cannot_sign_an_addendum_without_a_signature(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    provider = await _asked(harness, practice, note_id)

    refused = await harness.client.post("/api/respond", headers=provider, json={"answers": ANSWERS, "confirmed": True})

    assert (refused.status_code, refused.json()["error"]) == (409, "signature_required")
    async with SessionFactory() as db:
        assert (await db.scalars(select(ProviderAttestation))).all() == []
    assert await _events() == []


async def test_a_drawn_provider_signature_is_checked_and_seals_the_addendum(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    provider = await _asked(harness, practice, note_id)
    signature_id = await provider_signature(harness, provider, source="drawn")

    signed = await harness.client.post(
        "/api/respond", headers=provider, json={"answers": ANSWERS, "confirmed": True, "signature_id": signature_id}
    )

    assert signed.status_code == 200, signed.text
    assert harness.image_model.images == [signature_png()]
    [event] = await _events()
    async with SessionFactory() as db:
        attestation = await db.scalar(select(ProviderAttestation))
        note = await db.get_one(Note, note_id)
        signature = await db.get_one(Signature, signature_id)
    assert signature.file_key == f"practices/{practice.id}/signatures/{signature_id}.png"
    assert (event.event, event.record_id, event.signer_kind) == ("provider_addendum", attestation.id, "provider")
    assert (event.signer_name, event.signer_title, event.typed_name) == ("Elena Varga", "MD", "Elena Varga")
    assert (event.statement, event.document_sha256) == (ADDENDUM_ATTESTATION, note.file_sha256)
    assert json.loads(event.envelope)["signature_sha256"] == signature.sha256
    verified = (await harness.client.get(f"/api/verify/{event.code}")).json()
    assert (verified["valid"], verified["signer_name"], verified["event"]) == (True, "Elena Varga", "provider_addendum")


async def test_a_remembered_signature_is_offered_and_used_on_the_next_request(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    provider = await _asked(harness, practice, note_id)
    signature_id = await provider_signature(harness, provider)
    body = {"answers": ANSWERS, "confirmed": True, "signature_id": signature_id, "remember_signature": True}
    assert (await harness.client.post("/api/respond", headers=provider, json=body)).status_code == 200

    await read_next_note(harness, icd_catalog)
    assert (await turn_on_level_confirmation(harness, practice, hold=False)).status_code == 200
    await keep_i10_with_reason(harness, practice, note_id)
    assert (await approve(harness, practice, note_id)).status_code == 200
    second = await provider_session(harness, harness.messenger.last_fragment())
    shown = (await harness.client.get("/api/respond", headers=second)).json()
    answered = await harness.client.post(
        "/api/respond/level-change",
        headers=second,
        json={"answer": "confirm", "confirmed": True, "attestation": LEVEL_ATTESTATION},
    )

    assert (shown["signature"]["id"], shown["signature"]["image"]) == (signature_id, signature_data_url())
    assert answered.status_code == 200, answered.text
    provider_events = [event for event in await _events() if event.signer_kind == "provider"]
    assert [event.event for event in provider_events] == ["provider_addendum", "provider_level_change"]
    assert {event.signature_id for event in provider_events} == {signature_id}
    async with SessionFactory() as db:
        assert (
            len((await db.scalars(select(SignatureAdoption).where(SignatureAdoption.provider_id.is_not(None)))).all())
            == 1
        )


async def test_a_provider_cannot_sign_with_another_provider_s_signature(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    provider = await _asked(harness, practice, note_id)
    async with SessionFactory() as db:
        admin_signature = await db.scalar(select(Signature.id).where(Signature.user_id.is_not(None)))

    body = {"answers": ANSWERS, "confirmed": True, "signature_id": admin_signature}
    taken = await harness.client.post("/api/respond", headers=provider, json=body)

    assert taken.status_code == 404
