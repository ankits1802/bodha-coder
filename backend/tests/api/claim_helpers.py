from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.core.db import SessionFactory
from app.models import AccessLog, ClaimSubmission
from app.services.ack_polling import poll_acknowledgments
from tests.builders import DOCUMENTED, Harness, Practice, read_next_note, reviewed_note, upload_note
from tests.fakes import FAKE_HOST_KEY, NOTE_TEXT

BILLED = "99215, 96127x2, I10, E11.9, N18.30"
ELENA = {
    "name": "Elena Varga",
    "credential": "MD",
    "specialty": "Internal medicine",
    "npi": "1234567893",
    "place_code": "11",
    "email": "varga@clinic.example.com",
    "details": {"taxonomy_code": "207R00000X", "bills_under": "group", "group_npi": "1245319599"},
}
PRACTICE_DETAILS = {
    "legal_name": "Lakeside Family Medicine",
    "tax_id": "12-3456789",
    "group_npi": "1245319599",
    "taxonomy_code": "207Q00000X",
    "address": "123 Main St",
    "address_line_2": "Suite 200",
    "city": "Springfield",
    "state": "IL",
    "zip": "62701-1234",
    "phone": "(555) 555-1234",
    "billing_contact": "Dana Biller",
}
MEDICARE = {"name": "Medicare Part B", "payer_id": "MCRB", "plan_type": "medicare"}
SFTP = {
    "name": "Office Ally",
    "transport": "sftp",
    "usage": "test",
    "sender_id": "SUB123",
    "receiver_id": "OFFALLY",
    "receiver_name": "Office Ally",
    "host": "sftp.clearinghouse.example.com",
    "port": 22,
    "username": "lakeside",
    "auth_kind": "password",
    "password": "s3cret-pass-0001",
    "host_key_sha256": FAKE_HOST_KEY,
    "outbound_folder": "/outbound",
    "inbound_folder": "/inbound",
}
PORTAL = {
    "name": "Availity",
    "transport": "portal",
    "usage": "production",
    "sender_id": "AV123",
    "receiver_id": "030240928",
    "receiver_name": "Availity",
}
DETAILS = {
    "patient_last": "Reyes",
    "patient_first": "Marisol",
    "patient_birth_date": "1959-03-12",
    "patient_sex": "F",
    "street": "9 Elm St",
    "city": "Springfield",
    "state": "IL",
    "zip_code": "62704",
    "relationship": "18",
    "member_id": "1EG4-TE5-MK72",
}
CHARGES = {"99214": 15000, "96127": 1000}


def ok(response, status: int = 200) -> dict:
    assert response.status_code == status, response.text
    return response.json() if response.content and status != 204 else {}


async def approved_note(harness: Harness, icd_catalog) -> tuple[Practice, str]:
    practice, note_id = await reviewed_note(harness, icd_catalog)
    ok(await harness.client.put(f"/api/providers/{practice.provider_id}", headers=practice.admin, json=ELENA), 204)
    await approve_billed(harness, practice, note_id)
    return practice, note_id


async def approve_billed(harness: Harness, practice: Practice, note_id: str) -> None:
    body = {"codes": BILLED, "reason": DOCUMENTED}
    ok(await harness.client.put(f"/api/notes/{note_id}/billed-codes", headers=practice.admin, json=body))
    ok(await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin))


async def second_approved_note(harness: Harness, icd_catalog, practice: Practice) -> str:
    known = {item["id"] for item in ok(await harness.client.get("/api/notes", headers=practice.admin))["items"]}
    name = "2026-11-26 - REYES MARISOL - 99214 - Follow-up.pdf"
    ok(await upload_note(harness, practice, file_name=name, body=f"{NOTE_TEXT} Seen again."))
    await read_next_note(harness, icd_catalog)
    listed = ok(await harness.client.get("/api/notes", headers=practice.admin))["items"]
    note_id = next(item["id"] for item in listed if item["id"] not in known)
    await approve_billed(harness, practice, note_id)
    return note_id


async def set_up_billing(harness: Harness, practice: Practice, note_id: str, *, connection: dict) -> None:
    client, admin = harness.client, practice.admin
    ok(await client.put("/api/practice/setup/practice_details", headers=admin, json={"values": PRACTICE_DETAILS}), 204)
    payer = ok(await client.post("/api/practice/payers", headers=admin, json=MEDICARE))
    ok(await client.put(f"/api/notes/{note_id}/payer", headers=admin, json={"payer": payer["id"]}))
    for code, cents in CHARGES.items():
        ok(await client.put(f"/api/practice/charges/{code}", headers=admin, json={"cents": cents}))
    ok(await client.put("/api/practice/clearinghouse", headers=admin, json=connection))
    ok(await client.put(f"/api/notes/{note_id}/claim-details", headers=admin, json=DETAILS))


async def ready_claim(harness: Harness, icd_catalog, *, connection: dict = SFTP) -> tuple[Practice, str]:
    practice, note_id = await approved_note(harness, icd_catalog)
    await set_up_billing(harness, practice, note_id, connection=connection)
    return practice, note_id


async def billing_row(harness: Harness, practice: Practice, note_id: str, *, show: str = "ready") -> dict | None:
    listed = ok(await harness.client.get(f"/api/billing?show={show}", headers=practice.admin))
    return next((row for row in listed["items"] if row["id"] == note_id), None)


async def only_submission(practice: Practice) -> ClaimSubmission:
    async with SessionFactory() as db:
        rows = list(await db.scalars(select(ClaimSubmission).where(ClaimSubmission.practice_id == practice.id)))
    assert len(rows) == 1
    return rows[0]


async def access_entries(practice: Practice) -> list[AccessLog]:
    async with SessionFactory() as db:
        query = select(AccessLog).where(AccessLog.practice_id == practice.id).order_by(AccessLog.chain_seq)
        return list(await db.scalars(query))


async def poll(harness: Harness) -> int:
    async with SessionFactory() as db:
        return await poll_acknowledgments(db, harness.store, harness.link, datetime.now(UTC))
