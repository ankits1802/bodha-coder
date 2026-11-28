from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, date, datetime
from email.message import EmailMessage

import pytest
from sqlalchemy import select

from app.adapters.object_store import practice_prefix
from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import Batch, CodeSet, IntakeMessage, IntakeSender, Note
from app.services.email_intake import poll_email_intake
from app.services.email_intake_files import NO_PROVIDER, ONLY_PDF
from tests.builders import invite_member, practice_with_provider, sign_in
from tests.fakes import FakeListingStore, text_pdf

DOMAIN = "intake.example.com"
BASE = "/api/practice/email-intake"
NOW = datetime(2026, 11, 27, 15, 0, tzinfo=UTC)
SENDER = "scans@lakeside.example.com"
NOTE_NAME = "2026-11-20 - REYES MARISOL - 99214 - Progress.pdf"
PAGE_ONE = text_pdf("Elena Varga MD NPI 1234567893 Date of service 2026-11-20 Follow-up of diabetes")
NO_NAME_PAGE = text_pdf("Date of service 2026-11-20 Follow-up of diabetes")
PASSED = {"spam": "PASS", "virus": "PASS", "spf": "PASS", "dkim": "PASS", "dmarc": "PASS"}
ADDRESS_SHAPE = re.compile(r"^[a-z2-7]{16}@intake\.example\.com$")


@pytest.fixture
def intake_domain(monkeypatch) -> str:
    monkeypatch.setattr(get_settings(), "email_intake_domain", DOMAIN)
    return DOMAIN


def _mail(*, sender: str = SENDER, subject: str = "Visit notes", files=((PAGE_ONE, NOTE_NAME),)) -> EmailMessage:
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = sender, "front-desk@lakeside.example.com", subject
    message.set_content("Notes for today.")
    for data, name in files:
        subtype = "pdf" if name.endswith(".pdf") else "octet-stream"
        message.add_attachment(data, maintype="application", subtype=subtype, filename=name)
    return message


def _arrive(store: FakeListingStore, message_id: str, recipient: str, mail: EmailMessage, **verdicts: str) -> None:
    store.objects[f"ses-inbound/{message_id}"] = mail.as_bytes()
    envelope = {
        "version": 1,
        "message_id": message_id,
        "received_at": "2026-11-27T14:59:00Z",
        "recipients": [recipient],
        "verdicts": {**PASSED, **verdicts},
    }
    store.objects[f"ses-inbound/{message_id}.json"] = json.dumps(envelope).encode()


async def _poll(store: FakeListingStore) -> int:
    async with SessionFactory() as db:
        return await poll_email_intake(db, store, NOW)


async def _ready(harness, *, sender: str = "Lakeside.example.com"):
    practice = await practice_with_provider(harness)
    issued = await harness.client.post(f"{BASE}/address", headers=practice.admin)
    assert issued.status_code == 200, issued.text
    allowed = await harness.client.post(f"{BASE}/senders", headers=practice.admin, json={"sender": sender})
    assert allowed.status_code == 200, allowed.text
    return practice, issued.json()["address"]


async def _messages(harness, practice) -> list[dict]:
    response = await harness.client.get(f"{BASE}/messages", headers=practice.admin)
    assert response.status_code == 200, response.text
    return response.json()["items"]


async def test_an_admin_gets_an_unguessable_address_and_a_new_one_retires_the_old(harness, intake_domain):
    practice = await practice_with_provider(harness)
    first = (await harness.client.get(BASE, headers=practice.admin)).json()
    assert (first["available"], first["address"], first["previous"]) == (True, None, [])

    issued = (await harness.client.post(f"{BASE}/address", headers=practice.admin)).json()
    assert ADDRESS_SHAPE.fullmatch(issued["address"])
    rotated = (await harness.client.post(f"{BASE}/address", headers=practice.admin)).json()
    assert rotated["address"] != issued["address"] and ADDRESS_SHAPE.fullmatch(rotated["address"])
    assert [row["address"] for row in rotated["previous"]] == [issued["address"]]
    assert rotated["previous"][0]["until"] is not None

    off = await harness.client.delete(f"{BASE}/address", headers=practice.admin)
    assert off.status_code == 200, off.text
    assert off.json()["address"] is None
    assert [row["address"] for row in off.json()["previous"]] == [rotated["address"], issued["address"]]
    assert (await harness.client.delete(f"{BASE}/address", headers=practice.admin)).status_code == 404


async def test_email_intake_waits_for_bodha_to_have_an_intake_domain(harness):
    practice = await practice_with_provider(harness)
    assert (await harness.client.get(BASE, headers=practice.admin)).json()["available"] is False
    refused = await harness.client.post(f"{BASE}/address", headers=practice.admin)
    assert refused.status_code == 409
    assert refused.json()["message"] == "email intake is not set up for Bodha yet"


async def test_only_admins_set_up_email_intake(harness, intake_domain):
    practice = await practice_with_provider(harness)
    await invite_member(harness, practice, name="Casey Coder", email="coder@lakeside.example.com", role="coder")
    coder = await sign_in(harness.client, "coder@lakeside.example.com")
    assert (await harness.client.get(BASE, headers=coder)).status_code == 403
    assert (await harness.client.post(f"{BASE}/address", headers=coder)).status_code == 403
    assert (await harness.client.get(f"{BASE}/messages", headers=coder)).status_code == 403


async def test_allowed_senders_keep_their_history(harness, intake_domain):
    practice = await practice_with_provider(harness)
    added = await harness.client.post(
        f"{BASE}/senders", headers=practice.admin, json={"sender": "Scans@Lakeside.example.com"}
    )
    assert added.status_code == 200, added.text
    sender = added.json()["senders"][0]
    assert (sender["pattern"], sender["kind"]) == (SENDER, "address")
    repeat = await harness.client.post(f"{BASE}/senders", headers=practice.admin, json={"sender": SENDER})
    assert repeat.status_code == 409
    public = await harness.client.post(f"{BASE}/senders", headers=practice.admin, json={"sender": "gmail.com"})
    assert public.status_code == 422

    removed = await harness.client.delete(f"{BASE}/senders/{sender['id']}", headers=practice.admin)
    assert removed.status_code == 200, removed.text
    assert removed.json()["senders"] == []
    async with SessionFactory() as db:
        rows = (await db.scalars(select(IntakeSender))).all()
    assert [(row.pattern, row.removed_at is not None) for row in rows] == [(SENDER, True)]


async def test_a_pdf_from_an_allowed_sender_becomes_a_note_placed_from_page_one(harness, intake_domain):
    practice, address = await _ready(harness)
    store = FakeListingStore()
    raw = _mail()
    _arrive(store, "m-accepted", address, raw)

    assert await _poll(store) == 1

    async with SessionFactory() as db:
        note = await db.scalar(select(Note).where(Note.practice_id == practice.id))
        batch = await db.get_one(Batch, note.batch_id)
        billed = await db.scalar(select(CodeSet).where(CodeSet.note_id == note.id))
    checksum = hashlib.sha256(PAGE_ONE).hexdigest()
    assert (note.provider_id, note.service_date, note.place_code) == (practice.provider_id, date(2026, 11, 20), "11")
    assert (note.file_name, note.patient_name, batch.source, batch.created_by) == (
        f"{checksum} - 99214.pdf",
        None,
        "intake",
        None,
    )
    assert [code["code"] for code in billed.codes] == ["99214"]
    [row] = await _messages(harness, practice)
    assert (row["outcome"], row["reason"], row["sender"], row["accepted_files"]) == ("accepted", None, SENDER, 1)
    assert row["files"] == [{"outcome": "accepted", "reason": None, "note_id": note.id}]
    assert "subject" not in row and "body" not in row
    assert sorted(key for key in store.objects if key.startswith("ses-")) == ["ses-retained/m-accepted"]
    assert store.objects["ses-retained/m-accepted"] == raw.as_bytes()


async def test_mail_from_anyone_else_or_unchecked_mail_is_refused_recorded_and_never_read(harness, intake_domain):
    practice, address = await _ready(harness)
    store = FakeListingStore()
    _arrive(store, "m-stranger", address, _mail(sender="someone@elsewhere.example.org"))
    _arrive(store, "m-spoofed", address, _mail(), dmarc="FAIL")
    _arrive(store, "m-virus", address, _mail(), virus="FAIL")
    _arrive(store, "m-empty", address, _mail(files=()))

    assert await _poll(store) == 4

    reasons = {row["reason"] for row in await _messages(harness, practice)}
    assert reasons == {"sender_not_allowed", "not_authenticated", "failed_scan", "no_pdf"}
    async with SessionFactory() as db:
        assert await db.scalar(select(Note.id).where(Note.practice_id == practice.id)) is None
    assert sorted(store.objects) == [
        f"ses-retained/{name}" for name in ("m-empty", "m-spoofed", "m-stranger", "m-virus")
    ]


async def test_each_file_page_one_cannot_place_is_refused_with_its_reason(harness, intake_domain):
    practice, address = await _ready(harness)
    store = FakeListingStore()
    files = ((NO_NAME_PAGE, "scan.pdf"), (b"PK\x03\x04 word", "scan.docx"))
    _arrive(store, "m-unplaced", address, _mail(files=files))

    assert await _poll(store) == 1

    [row] = await _messages(harness, practice)
    assert (row["outcome"], row["reason"], row["accepted_files"], row["refused_files"]) == (
        "refused",
        "files_refused",
        0,
        2,
    )
    assert [file["reason"] for file in row["files"]] == [NO_PROVIDER, ONLY_PDF]


async def test_mail_to_a_retired_or_unknown_address_is_recorded_but_not_read(harness, intake_domain):
    practice, old_address = await _ready(harness)
    assert (await harness.client.post(f"{BASE}/address", headers=practice.admin)).status_code == 200
    store = FakeListingStore()
    _arrive(store, "m-old", old_address, _mail())
    _arrive(store, "m-nobody", f"nobody@{DOMAIN}", _mail())

    assert await _poll(store) == 2

    assert [row["reason"] for row in await _messages(harness, practice)] == ["retired_address"]
    async with SessionFactory() as db:
        stray = await db.scalar(select(IntakeMessage).where(IntakeMessage.message_key == "m-nobody"))
        notes = await db.scalar(select(Note.id).where(Note.practice_id == practice.id))
    assert (stray.practice_id, stray.address_id, stray.sender, stray.reason) == (None, None, None, "unknown_address")
    assert notes is None


async def test_a_test_message_from_bodha_confirms_the_address_receives_mail(harness, intake_domain):
    practice, address = await _ready(harness)
    sent = await harness.client.post(f"{BASE}/tests", headers=practice.admin)
    assert sent.status_code == 200, sent.text
    assert sent.json()["arrived_at"] is None
    assert harness.messenger.sent[-1][0] == address
    store = FakeListingStore()
    probe = _mail(sender="no-reply@bodhaai.co", subject=f"Re: {harness.messenger.subjects[-1]}", files=())
    _arrive(store, "m-probe", address, probe, dmarc="GRAY")

    assert await _poll(store) == 1

    checked = await harness.client.get(f"{BASE}/tests/{sent.json()['id']}", headers=practice.admin)
    assert checked.json()["arrived_at"] is not None
    [row] = await _messages(harness, practice)
    assert (row["outcome"], row["reason"], row["files"]) == ("test", None, [])


async def test_a_message_seen_twice_is_recorded_and_read_once(harness, intake_domain):
    practice, address = await _ready(harness)
    store = FakeListingStore()
    _arrive(store, "m-twice", address, _mail())
    assert await _poll(store) == 1
    _arrive(store, "m-twice", address, _mail())
    assert await _poll(store) == 1

    assert len(await _messages(harness, practice)) == 1
    async with SessionFactory() as db:
        notes = (await db.scalars(select(Note.id).where(Note.practice_id == practice.id))).all()
    assert len(notes) == 1


async def test_mail_is_read_from_its_own_store_and_kept_with_the_documents(harness, intake_domain):
    practice, address = await _ready(harness)
    inbound, documents = FakeListingStore(), FakeListingStore()
    raw = _mail()
    _arrive(inbound, "m-split", address, raw)

    async with SessionFactory() as db:
        assert await poll_email_intake(db, documents, NOW, inbound=inbound) == 1

    assert inbound.objects == {}
    assert documents.objects["ses-retained/m-split"] == raw.as_bytes()
    assert any(key.startswith(practice_prefix(practice.id)) for key in documents.objects)
