from __future__ import annotations

import io
import re

from pypdf import PdfReader

from tests.builders import practice_with_provider, read_next_note, reviewed_note

QUESTION = "What stage is the kidney disease?"
SIGNED_ADDENDUM = re.compile(
    r"Addendum \(amendment to the original note\) · signed \d{2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}"
)


async def _signed_addendum(harness, practice, note_id, icd_catalog) -> None:
    asked = await harness.client.post(
        f"/api/notes/{note_id}/ask",
        headers=practice.admin,
        json={"questions": [{"key": "dx:N18.30", "text": QUESTION}], "channel": "email", "hold": True},
    )
    assert asked.status_code == 200, asked.text
    token = harness.messenger.last_fragment()
    await harness.client.post("/api/respond/code", json={"token": token})
    verified = await harness.client.post(
        "/api/respond/verify", json={"token": token, "code": harness.messenger.last_code()}
    )
    provider = {"Authorization": f"Bearer {verified.json()['provider_token']}"}
    answered = await harness.client.post(
        "/api/respond", headers=provider, json={"answers": [{"key": "dx:N18.30", "choice": "Yes"}], "confirmed": True}
    )
    assert answered.json()["status"] == "answered", answered.text
    await read_next_note(harness, icd_catalog)


def _pages(content: bytes) -> list[str]:
    return [" ".join((page.extract_text() or "").split()) for page in PdfReader(io.BytesIO(content)).pages]


async def test_the_packet_defends_the_approved_claim_with_its_evidence_and_the_signed_addendum(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await _signed_addendum(harness, practice, note_id, icd_catalog)
    approved = await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)
    assert approved.json() == {"status": "approved"}, approved.text

    response = await harness.client.get(f"/api/notes/{note_id}/defense-packet", headers=practice.admin)

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    file_name = f"bodha-defense-packet-20261125-{note_id[:8]}.pdf"
    assert response.headers["content-disposition"] == f'attachment; filename="{file_name}"'
    cover, *rest = _pages(response.content)
    inside = " ".join(rest)
    assert "Patient R.M." in cover and "Date of service 25 Nov 2026" in cover
    assert "Reyes" not in cover and "Marisol" not in cover
    assert "prompt version test" in cover
    assert "Patient Reyes Marisol" in inside
    assert "Final claim" in inside and "Billed codes" in inside
    assert "Visit level · 99215 → 99214 · Accepted by default" in inside
    assert "“increase metformin”" in inside
    assert "ICD-10-CM FY2027 release (CDC) for the date of service" in inside
    assert SIGNED_ADDENDUM.search(inside)
    assert f"{QUESTION} Yes." in inside


async def test_downloading_the_packet_is_written_to_the_access_log(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)

    response = await harness.client.get(f"/api/notes/{note_id}/defense-packet", headers=practice.admin)

    assert response.status_code == 200, response.text
    assert "Claim as decided, not approved" in " ".join(_pages(response.content))
    log = (await harness.client.get("/api/access-log", headers=practice.admin)).json()["items"]
    assert any(row["action"] == "downloaded defense packet" for row in log)


async def test_another_practice_cannot_download_the_packet(harness, icd_catalog):
    _, note_id = await reviewed_note(harness, icd_catalog)
    other = await practice_with_provider(harness, name="Hillcrest", admin_email="admin@hillcrest.example.com")

    response = await harness.client.get(f"/api/notes/{note_id}/defense-packet", headers=other.admin)

    assert response.status_code == 404
