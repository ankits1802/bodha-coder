import io
import json
import zipfile

from pypdf import PdfReader
from sqlalchemy import select

from app.core.db import SessionFactory
from app.models import Practice, SigningEvent
from tests.api.review_helpers import approve
from tests.builders import reviewed_note


def _text(content: bytes) -> str:
    return " ".join(" ".join((page.extract_text() or "").split()) for page in PdfReader(io.BytesIO(content)).pages)


async def _approved_event(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    assert (await approve(harness, practice, note_id)).status_code == 200
    async with SessionFactory() as db:
        event = await db.scalar(select(SigningEvent))
    return practice, note_id, event


async def test_the_defense_packet_ends_with_a_certificate_of_review_for_each_signature(harness, icd_catalog):
    practice, note_id, event = await _approved_event(harness, icd_catalog)

    packet = await harness.client.get(f"/api/notes/{note_id}/defense-packet", headers=practice.admin)

    text = _text(packet.content)
    assert "Certificate of review" in text
    assert "Claim approved" in text and "Practice Admin (admin)" in text
    assert event.code in text and f"/verify?code={event.code}" in text
    assert event.envelope_sha256[:40] in text and event.document_sha256[:40] in text
    assert "Adopted by typing the name" in text


async def test_the_audit_package_carries_each_certificate_and_the_sealed_envelopes(harness, icd_catalog):
    practice, note_id, event = await _approved_event(harness, icd_catalog)

    response = await harness.client.post(f"/api/notes/{note_id}/audit-package", headers=practice.admin)

    archive = zipfile.ZipFile(io.BytesIO(response.content))
    certificate = archive.read(f"certificates/{event.code}.pdf")
    assert "Certificate of review" in _text(certificate)
    [sealed] = json.loads(archive.read("signing-events.json"))
    assert (sealed["code"], sealed["envelope"], sealed["seal"]) == (event.code, event.envelope, event.seal)
    manifest = {item["path"] for item in json.loads(archive.read("manifest.json"))["files"]}
    assert {f"certificates/{event.code}.pdf", "signing-events.json"} <= manifest


async def test_accepting_the_agreement_at_sign_up_is_sealed(harness):
    body = {
        "name": "Rosa Diaz",
        "practice_name": "Lakeside Family Medicine",
        "email": "rosa@lakeside.example.com",
        "time_zone": "America/Denver",
        "agreed": True,
    }

    assert (await harness.client.post("/api/signup", json=body)).status_code == 204

    async with SessionFactory() as db:
        practice = await db.scalar(select(Practice))
        [event] = (await db.scalars(select(SigningEvent))).all()
    assert (event.event, event.record_id, event.note_id, event.signature_id) == ("agreement", practice.id, None, None)
    assert (event.signer_name, event.typed_name, event.signer_title) == ("Rosa Diaz", "Rosa Diaz", "admin")
    assert "version unpublished" in event.statement
    verified = (await harness.client.get(f"/api/verify/{event.code}")).json()
    assert (verified["valid"], verified["event"], verified["practice_name"]) == (
        True,
        "agreement",
        "Lakeside Family Medicine",
    )
