from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select

from app.core.db import SessionFactory
from app.models import AccessLog, Batch, CodeSet, Note
from app.services.intake import arrival_name, poll_intake, sort_inbox
from app.services.intake_settings import IntakeConfig
from tests.builders import Practice, practice_with_provider
from tests.fakes import FakeListingStore, text_pdf

NOW = datetime(2026, 11, 27, 15, 0, tzinfo=UTC)
NOTE_NAME = "2026-11-20 - REYES MARISOL - 99214 - Progress.pdf"
DROPPED_PDF = text_pdf("Follow-up visit for diabetes.")


class UnreadableArrivals(FakeListingStore):
    def __init__(self) -> None:
        super().__init__()
        self.unreadable = True

    async def get(self, key: str) -> bytes:
        if self.unreadable and key.endswith(" - 99214.pdf"):
            raise OSError("storage unavailable")
        return await super().get(key)


class LossyCopies(FakeListingStore):
    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        await super().put(key, data[:-1] if "/processed/" in key else data, content_type=content_type)


def _checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def _turn_on(harness, practice, **changes):
    values = {
        "enabled": True,
        "prefix": "inbox",
        "provider_by_folder": {"varga": practice.provider_id},
        "place_code": "11",
        "visit_type": "Established patient",
        **changes,
    }
    return await harness.client.put("/api/practice/intake", headers=practice.admin, json=values)


async def _poll(store: FakeListingStore) -> int:
    async with SessionFactory() as db:
        return await poll_intake(db, store, NOW)


def _under(store: FakeListingStore, prefix: str) -> list[str]:
    return sorted(key for key in store.objects if key.startswith(prefix))


async def test_the_inbox_settings_are_saved_and_checked(harness):
    practice = await practice_with_provider(harness)
    saved = await _turn_on(harness, practice)
    assert saved.status_code == 200, saved.text
    assert "watched_prefix" not in saved.json()
    stored = (await harness.client.get("/api/practice/intake", headers=practice.admin)).json()
    assert stored["provider_by_folder"] == {"varga": practice.provider_id}
    assert (stored["enabled"], stored["place_code"]) == (True, "11")

    assert (
        await _turn_on(harness, practice, provider_by_folder={"processed": practice.provider_id})
    ).status_code == 422
    assert (await _turn_on(harness, practice, provider_by_folder={"varga": "not-a-provider"})).status_code == 404
    assert (await _turn_on(harness, practice, place_code=None)).status_code == 422
    assert (await _turn_on(harness, practice, prefix="notes")).status_code == 422


def _reasons(store: FakeListingStore, prefix: str) -> list[str]:
    return [store.objects[key].decode() for key in _under(store, prefix) if key.endswith(".reason.txt")]


async def _mixed_inbox(harness) -> tuple[Practice, str, FakeListingStore]:
    practice = await practice_with_provider(harness)
    assert (await _turn_on(harness, practice)).status_code == 200
    inbox = f"practices/{practice.id}/inbox/"
    store = FakeListingStore()
    store.objects.update(
        {
            f"{inbox}varga/2026-11-20/{NOTE_NAME}": DROPPED_PDF,
            f"{inbox}varga/2026-11-20/scan.docx": b"word file",
            f"{inbox}varga/2026-11-20/fake.pdf": b"not a pdf",
            f"{inbox}unknown/2026-11-20/other.pdf": text_pdf("Another note."),
            f"{inbox}varga/2026-12-01/later.pdf": text_pdf("A later note."),
        }
    )
    assert await _poll(store) == 1
    return practice, inbox, store


async def test_a_dropped_pdf_becomes_a_note_uploaded_by_intake(harness):
    practice, inbox, store = await _mixed_inbox(harness)

    async with SessionFactory() as db:
        note = await db.scalar(select(Note).where(Note.practice_id == practice.id))
        batch = await db.get_one(Batch, note.batch_id)
        billed = await db.scalar(select(CodeSet).where(CodeSet.note_id == note.id))
        entry = await db.scalar(select(AccessLog).where(AccessLog.action == "uploaded notes"))
    renamed = f"{_checksum(DROPPED_PDF)} - 99214.pdf"
    assert (note.service_date, note.patient_name, note.file_name) == (date(2026, 11, 20), None, renamed)
    assert [(code["code"], code["type"]) for code in billed.codes] == [("99214", "CPT")]
    assert (batch.provider_id, batch.place_code, batch.source, batch.created_by) == (
        practice.provider_id,
        "11",
        "intake",
        None,
    )
    assert (billed.actor_id, entry.practice_id, entry.actor_kind, entry.actor_id, entry.actor_name) == (
        None,
        practice.id,
        "system",
        "bodha-intake",
        "Bodha intake",
    )
    history = (await harness.client.get("/api/batches", headers=practice.admin)).json()["items"]
    assert [row["uploaded_by"] for row in history] == ["Intake"]
    assert store.objects[note.file_key] == DROPPED_PDF
    processed = _under(store, f"{inbox}processed/2026-11-27/")
    assert len(processed) == 1 and store.objects[processed[0]] == DROPPED_PDF
    assert not any("REYES" in key or "Progress" in key for key in store.objects)


async def test_everything_else_is_moved_to_rejected_with_a_reason(harness):
    _, inbox, store = await _mixed_inbox(harness)

    left = [
        key for key in store.objects if key.startswith(inbox) and "/processed/" not in key and "/rejected/" not in key
    ]
    assert left == []
    reasons = _reasons(store, f"{inbox}rejected/2026-11-27/")
    assert len(reasons) == 4
    word = f"file: varga/2026-11-20/{_checksum(b'word file')}.docx\nreason: only PDF files are read"
    assert any(word in text for text in reasons)
    assert any(f"reason: {_checksum(b'not a pdf')}.pdf is not a PDF" in text for text in reasons)
    assert any("reason: no provider is set for the folder unknown" in text for text in reasons)
    assert any("reason: the date of service 2026-12-01 is in the future" in text for text in reasons)
    for dropped_name in ("scan", "fake", "other", "later"):
        assert not any(dropped_name in text for text in reasons)
        assert not any(dropped_name in key for key in store.objects)


async def test_a_dropped_file_is_renamed_to_its_checksum_before_it_is_read(harness):
    practice = await practice_with_provider(harness)
    assert (await _turn_on(harness, practice)).status_code == 200
    folder = f"practices/{practice.id}/inbox/varga/2026-11-20/"
    store = UnreadableArrivals()
    store.objects[f"{folder}{NOTE_NAME}"] = DROPPED_PDF

    with pytest.raises(OSError):
        await _poll(store)
    assert sorted(store.objects) == sorted([f"{folder}{NOTE_NAME}", f"{folder}{_checksum(DROPPED_PDF)} - 99214.pdf"])

    store.unreadable = False
    assert await _poll(store) == 1
    async with SessionFactory() as db:
        note = await db.scalar(select(Note).where(Note.practice_id == practice.id))
        billed = await db.scalar(select(CodeSet).where(CodeSet.note_id == note.id))
    assert [code["code"] for code in billed.codes] == ["99214"]


async def test_an_arrival_stays_in_the_inbox_when_its_kept_copy_does_not_match(harness):
    practice = await practice_with_provider(harness)
    assert (await _turn_on(harness, practice)).status_code == 200
    folder = f"practices/{practice.id}/inbox/varga/2026-11-20/"
    store = LossyCopies()
    store.objects[f"{folder}{NOTE_NAME}"] = DROPPED_PDF

    with pytest.raises(OSError):
        await _poll(store)

    assert store.objects[f"{folder}{_checksum(DROPPED_PDF)} - 99214.pdf"] == DROPPED_PDF


def test_an_arrival_keeps_only_its_checksum_its_code_and_its_type():
    data = b"%PDF-1.7 visit"
    checksum = hashlib.sha256(data).hexdigest()
    assert arrival_name(NOTE_NAME, data) == f"{checksum} - 99214.pdf"
    assert arrival_name("Reyes Marisol.PDF", data) == f"{checksum}.pdf"
    assert arrival_name("Reyes Marisol 99214.docx", data) == f"{checksum}.docx"
    assert arrival_name("no suffix", data) == checksum


async def test_a_second_poll_does_nothing_and_a_dropped_duplicate_is_rejected(harness):
    practice = await practice_with_provider(harness)
    assert (await _turn_on(harness, practice)).status_code == 200
    inbox = f"practices/{practice.id}/inbox/"
    store = FakeListingStore()
    pdf = text_pdf("Follow-up visit for diabetes.")
    store.objects[f"{inbox}varga/2026-11-20/{NOTE_NAME}"] = pdf
    assert await _poll(store) == 1
    assert await _poll(store) == 0

    store.objects[f"{inbox}varga/2026-11-20/copy.pdf"] = pdf
    assert await _poll(store) == 0
    reasons = _reasons(store, f"{inbox}rejected/")
    assert reasons and "reason: this PDF was already uploaded" in reasons[0]


async def test_two_workers_polling_at_once_ingest_each_file_once(harness):
    practice = await practice_with_provider(harness)
    assert (await _turn_on(harness, practice)).status_code == 200
    store = FakeListingStore()
    store.objects[f"practices/{practice.id}/inbox/varga/2026-11-20/{NOTE_NAME}"] = text_pdf("One visit.")

    results = await asyncio.gather(_poll(store), _poll(store))

    assert sum(results) == 1
    async with SessionFactory() as db:
        assert len((await db.scalars(select(Note.id).where(Note.practice_id == practice.id))).all()) == 1


async def test_a_practice_with_intake_off_is_not_polled(harness):
    practice = await practice_with_provider(harness)
    assert (await _turn_on(harness, practice, enabled=False)).status_code == 200
    store = FakeListingStore()
    key = f"practices/{practice.id}/inbox/varga/2026-11-20/{NOTE_NAME}"
    store.objects[key] = text_pdf("One visit.")
    assert await _poll(store) == 0
    assert key in store.objects


def test_the_inbox_is_sorted_into_visit_days_and_rejects():
    inbox = "practices/p1/inbox/"
    config = IntakeConfig(enabled=True, provider_by_folder={"varga": "prov-1"}, place_code="11")
    keys = [
        f"{inbox}varga/2026-11-20/b.pdf",
        f"{inbox}varga/2026-11-20/a.PDF",
        f"{inbox}varga/2026-11-19/c.pdf",
        f"{inbox}varga/",
        f"{inbox}processed/2026-11-27/abc.pdf",
        f"{inbox}rejected/2026-11-27/abc.pdf",
        f"{inbox}loose.pdf",
        f"{inbox}varga/20-11-2026/d.pdf",
    ]

    found = sort_inbox(inbox, keys, config, date(2026, 11, 27))

    assert [(group.provider_id, group.service_date, group.keys) for group in found.groups] == [
        ("prov-1", date(2026, 11, 19), (f"{inbox}varga/2026-11-19/c.pdf",)),
        ("prov-1", date(2026, 11, 20), (f"{inbox}varga/2026-11-20/a.PDF", f"{inbox}varga/2026-11-20/b.pdf")),
    ]
    assert found.rejects == (
        (f"{inbox}loose.pdf", "files go in <provider folder>/<YYYY-MM-DD>/<file>.pdf"),
        (f"{inbox}varga/20-11-2026/d.pdf", "20-11-2026 is not a date (YYYY-MM-DD)"),
    )
