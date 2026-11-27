from sqlalchemy import select

from app.core.db import SessionFactory
from app.models import NoteText, ProviderAttestation
from app.services.attestations import ADDENDUM_ATTESTATION
from tests.api.review_helpers import provider_session, provider_signature
from tests.builders import reviewed_note

QUESTION = {"key": "dx:N18.30", "text": "What stage is the kidney disease?"}
ANSWERS = [{"key": "dx:N18.30", "choice": "Yes"}]


async def _asked(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    asked = await harness.client.post(
        f"/api/notes/{note_id}/ask", headers=practice.admin, json={"questions": [QUESTION], "channel": "email"}
    )
    assert asked.status_code == 200, asked.text
    return note_id, await provider_session(harness, harness.messenger.last_fragment())


async def test_signing_stores_the_exact_wording_the_texts_shown_and_the_address(harness, icd_catalog):
    note_id, provider = await _asked(harness, icd_catalog)
    async with SessionFactory() as db:
        shown_texts = list((await db.scalars(select(NoteText.id).where(NoteText.note_id == note_id))).all())

    opened = (await harness.client.get("/api/respond", headers=provider)).json()
    signature_id = await provider_signature(harness, provider)
    signed = await harness.client.post(
        "/api/respond",
        headers=provider,
        json={
            "answers": ANSWERS,
            "confirmed": True,
            "attestation": opened["attestation"],
            "signature_id": signature_id,
        },
    )

    assert (opened["purpose"], opened["attestation"], opened["level_change"]) == (
        "questions",
        ADDENDUM_ATTESTATION,
        None,
    )
    assert signed.status_code == 200, signed.text
    async with SessionFactory() as db:
        [statement] = (await db.scalars(select(ProviderAttestation))).all()
    assert (statement.purpose, statement.answer, statement.wording, statement.confirmed) == (
        "questions",
        "signed",
        ADDENDUM_ATTESTATION,
        True,
    )
    assert statement.shown == signed.json()["addendum_text"]
    assert (statement.text_revision_ids, statement.ip) == (shown_texts, "127.0.0.1")


async def test_a_page_showing_other_wording_cannot_sign(harness, icd_catalog):
    _, provider = await _asked(harness, icd_catalog)

    refused = await harness.client.post(
        "/api/respond",
        headers=provider,
        json={"answers": ANSWERS, "confirmed": True, "attestation": "I agree to anything"},
    )

    assert refused.status_code == 409
    async with SessionFactory() as db:
        assert (await db.scalars(select(ProviderAttestation))).all() == []


async def test_questions_cannot_be_answered_as_a_level_confirmation(harness, icd_catalog):
    _, provider = await _asked(harness, icd_catalog)

    refused = await harness.client.post(
        "/api/respond/level-change", headers=provider, json={"answer": "confirm", "confirmed": True}
    )

    assert refused.status_code == 409
