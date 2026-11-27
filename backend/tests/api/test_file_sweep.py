from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

from app.adapters.object_listing import StoredObject
from app.core.db import SessionFactory
from app.models import Activity, EvalRun, Practice
from app.services.file_sweep import StoredFile, classify_key, sweep_orphan_files
from tests.api.remittance_helpers import era, post_era
from tests.builders import maintenance, reviewed_note
from tests.fakes import FakeStore, text_pdf

NOW = datetime(2026, 11, 28, 3, 0, tzinfo=UTC)
OLD = NOW - timedelta(days=2)
RECENT = NOW - timedelta(hours=1)
GONE = "00000000-0000-4000-8000-0000000000a1"
STRANGER = "00000000-0000-4000-8000-0000000000b2"
GHOST = "00000000-0000-4000-8000-0000000000c3"


class AgedStore(FakeStore):
    def __init__(self, objects: dict[str, bytes], *, page_size: int = 3) -> None:
        super().__init__()
        self.objects.update(objects)
        self.modified = dict.fromkeys(objects, OLD)
        self.page_size = page_size

    def add(self, key: str, modified: datetime = OLD) -> None:
        self.objects[key], self.modified[key] = b"stored", modified

    async def list_keys(self, prefix: str) -> list[str]:
        return sorted(key for key in self.objects if key.startswith(prefix))

    async def object_pages(self, prefix: str) -> AsyncIterator[list[StoredObject]]:
        keys = await self.list_keys(prefix)
        for start in range(0, len(keys), self.page_size):
            yield [StoredObject(key, self.modified[key]) for key in keys[start : start + self.page_size]]

    async def list_folders(self, prefix: str) -> list[str]:
        return sorted({key[: key.index("/", len(prefix)) + 1] for key in self.objects if key.startswith(prefix)})


async def _evaluation_and_old_practices(practice_id: str) -> tuple[str, str]:
    async with SessionFactory() as db:
        run = EvalRun(
            practice_id=practice_id,
            model="fake-gemini",
            prompt_version="test",
            status="done",
            results=[{"case_id": "case-1"}],
        )
        db.add(run)
        db.add(Activity(actor_name="Bodha Admin", action="practice deleted", practice_id=GONE, detail="Old clinic"))
        await maintenance(db)
        purged = Practice(
            name="Purged clinic",
            status="purged",
            plan="professional",
            closed_at=OLD - timedelta(days=2600),
            purged_at=OLD,
        )
        db.add(purged)
        await db.commit()
        return run.id, purged.id


async def _amend_twice(harness, practice, note_id: str) -> None:
    for text in ("First amendment.", "Second amendment."):
        replaced = await harness.client.post(
            f"/api/notes/{note_id}/document",
            headers=practice.admin,
            files={"file": ("amended.pdf", text_pdf(text), "application/pdf")},
        )
        assert replaced.status_code == 200, replaced.text


def _orphans(root: str, purged_root: str) -> set[str]:
    return {
        f"{root}notes/{GHOST}/document.pdf",
        f"{root}notes/{GHOST}/analyses/1.prompt.json",
        f"{root}remittances/{GHOST}.835",
        f"{root}evaluations/{GHOST}/case-1-1.json",
        f"{purged_root}notes/{GHOST}/document.pdf",
    }


def _left_alone(root: str, note: str, run_id: str) -> set[str]:
    return {
        f"{note}document-r9.pdf",
        f"{note}analyses/7.json",
        f"{note}analyses/1.prompt.json",
        f"{root}evaluations/{run_id}/case-2-1.json",
        f"{root}inbox/varga/2026-11-20/dropped.pdf",
        f"{root}inbox-west/processed/2026-11-20/{'a' * 64}.pdf",
        f"{root}exports/summary.csv",
        f"practices/{STRANGER}/notes/{GHOST}/document.pdf",
        f"practices/{GONE}/notes/{GHOST}/document.pdf",
        f"practices/{GONE}/inbox/varga/2026-11-20/dropped.pdf",
    }


async def test_the_sweep_keeps_every_file_a_record_holds_and_deletes_only_true_orphans(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await _amend_twice(harness, practice, note_id)
    voided = await harness.client.post(
        "/api/notes/void", headers=practice.admin, json={"note_ids": [note_id], "reason": "a duplicate upload"}
    )
    assert voided.status_code == 200, voided.text
    remittance_id = (await post_era(harness, practice.admin, era())).json()["ids"][0]
    run_id, purged_id = await _evaluation_and_old_practices(practice.id)
    root, note = f"practices/{practice.id}/", f"practices/{practice.id}/notes/{note_id}/"
    stored_by_the_app = {
        f"{note}document.pdf",
        f"{note}document-r2.pdf",
        f"{note}document-r3.pdf",
        f"{note}analyses/1.json",
        f"{root}remittances/{remittance_id}.835",
    }
    assert stored_by_the_app <= set(harness.store.objects)
    store = AgedStore(harness.store.objects)
    replies = {f"{root}evaluations/{run_id}/case-1-1.json", f"{root}evaluations/{run_id}/case-1-2.json"}
    orphans, left_alone = _orphans(root, f"practices/{purged_id}/"), _left_alone(root, note, run_id)
    recent = {f"{root}notes/{STRANGER}/document.pdf", f"practices/{GONE}/notes/{STRANGER}/document.pdf"}
    for key in replies | orphans | left_alone:
        store.add(key)
    for key in recent:
        store.add(key, RECENT)
    before = set(store.objects)

    async with SessionFactory() as db:
        assert await sweep_orphan_files(db, store, NOW) == len(orphans)
    assert before - set(store.objects) == orphans
    assert stored_by_the_app | replies | left_alone | recent <= set(store.objects)
    async with SessionFactory() as db:
        assert await sweep_orphan_files(db, store, NOW) == 0


def test_keys_are_classified_by_their_shape():
    root = "practices/p-1/"
    assert classify_key("p-1", f"{root}notes/n-1/document-r12.pdf") == StoredFile(
        f"{root}notes/n-1/document-r12.pdf", "document", "n-1", "12"
    )
    assert classify_key("p-1", f"{root}notes/n-1/document.pdf").detail is None
    assert classify_key("p-1", f"{root}notes/n-1/analyses/3.prompt.json") == StoredFile(
        f"{root}notes/n-1/analyses/3.prompt.json", "prompt", "n-1", "3"
    )
    assert classify_key("p-1", f"{root}evaluations/r-1/c-1-0a-2.json").detail == "c-1-0a"
    assert classify_key("p-1", f"{root}remittances/r-9.835").owner == "r-9"
    assert classify_key("p-1", f"{root}inbox-2/varga/x.pdf").kind == "intake"
    assert classify_key("p-1", f"{root}notes/n-1/document-r0.pdf").kind == "unknown"
    assert classify_key("p-1", f"{root}notes/n-1/extra/document.pdf").kind == "unknown"
    assert classify_key("p-1", "practices/p-2/notes/n-1/document.pdf").kind == "unknown"
