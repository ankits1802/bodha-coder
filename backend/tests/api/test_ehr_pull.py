from __future__ import annotations

import base64
import hashlib
import logging
from datetime import UTC, datetime, time, timedelta
from io import BytesIO
from urllib.parse import urlsplit

import httpx
import pytest
from pypdf import PdfReader
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.core.db import SessionFactory
from app.models import Batch, EhrConnection, EhrDocument, EhrKey, EhrPullRun, Note
from app.services.ehr_pull import SETTLE
from tests.api.ehr_helpers import (
    API,
    CHICAGO,
    NOTE_PDF,
    NOW,
    OTHER_PDF,
    SEEN,
    START,
    TODAY,
    connected,
    documents,
    one_note,
    poll,
    pull_again,
    runs,
    visit,
)
from tests.builders import backdate_closure, sign_in
from tests.ehr_fakes import attachment, document, encounter, practitioner

STRANGER_NPI = "1245319599"
EMERGENCY_NOTE = b"<html><body><h1>Emergency visit</h1><p>Chest pain, troponin negative.</p></body></html>"


def _instant(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _start_of(day) -> datetime:
    return datetime.combine(day, time.min, tzinfo=CHICAGO)


def _unplaceable() -> list[dict]:
    return [
        document("d-preliminary", doc_status="preliminary"),
        document("d-stranger", author="Practitioner/p9"),
        document("d-undated", encounter=None),
        document("d-rtf", content=[attachment("Binary/r1", "text/rtf")]),
        document("d-empty", content=[]),
        document("d-gone", content=[attachment("Binary/missing")]),
        document("d-foreign", encounter="https://other.example.com/fhir/r4/Encounter/e1"),
        document("d-future", encounter="Encounter/e2"),
        document("d-altered", content=[attachment("Binary/b1", hash="AAAAAAAAAAAAAAAAAAAAAAAAAAA=")]),
        document("d-huge", content=[attachment("Binary/b1", size=10**10)]),
        document("d-consult", code="11488-4"),
    ]


async def _notes(practice_id: str) -> list[Note]:
    async with SessionFactory() as db:
        return list((await db.scalars(select(Note).where(Note.practice_id == practice_id))).all())


async def test_a_final_progress_note_becomes_a_note_from_the_ehr(harness, ehr):
    practice = await connected(harness)
    one_note(ehr)

    assert await poll(harness) == 1

    [note] = await _notes(practice.id)
    async with SessionFactory() as db:
        batch = await db.get_one(Batch, note.batch_id)
        record = await db.scalar(select(EhrDocument))
        run = await db.scalar(select(EhrPullRun))
    assert (note.provider_id, note.service_date, note.place_code) == (practice.provider_id, SEEN, "11")
    assert (batch.source, batch.created_by, note.file_sha256) == ("fhir", None, hashlib.sha256(NOTE_PDF).hexdigest())
    assert harness.store.objects[note.file_key] == NOTE_PDF
    assert (record.document_id, record.document_version, record.encounter_id, record.practitioner_id) == (
        "d1",
        "1",
        "e1",
        "p1",
    )
    assert (run.outcome, run.reason, run.accepted, run.pages, run.cursor) == ("succeeded", None, 1, 1, NOW - SETTLE)
    [row] = await documents(harness, practice)
    assert (row["document_id"], row["outcome"], row["reason"], row["note_id"]) == ("d1", "accepted", None, note.id)
    [search] = ehr.searches
    assert search["status"] == ["current"]
    assert search["type"] == ["http://loinc.org|11506-3"]
    assert search["date"] == [f"ge{START.isoformat()}"]
    assert search["_lastUpdated"] == [f"ge{_instant(_start_of(START))}", f"lt{_instant(NOW - SETTLE)}"]
    history = (await harness.client.get("/api/batches", headers=practice.admin)).json()["items"]
    assert [item["uploaded_by"] for item in history] == ["EHR"]


async def test_the_next_pull_resumes_from_the_cursor_and_skips_what_it_already_recorded(harness, ehr):
    practice = await connected(harness)
    one_note(ehr)
    await poll(harness)
    later = NOW + timedelta(minutes=20)

    assert await pull_again(harness, practice, later) == 0

    assert ehr.searches[1]["_lastUpdated"] == [f"ge{_instant(NOW - SETTLE)}", f"lt{_instant(later - SETTLE)}"]
    assert [request.url.path for request in ehr.requests].count("/fhir/r4/Binary/b1") == 1
    assert len(await documents(harness, practice)) == 1
    assert [(run["outcome"], run["accepted"]) for run in await runs(harness, practice)] == [
        ("succeeded", 0),
        ("succeeded", 1),
    ]


async def test_notes_of_one_visit_day_share_a_batch_across_pages(harness, ehr):
    practice = await connected(harness)
    visit(ehr)
    ehr.page_size = 1
    ehr.binaries.update({"Binary/b1": (NOTE_PDF, "application/pdf"), "Binary/b2": (OTHER_PDF, "application/pdf")})
    ehr.documents += [document("d1"), document("d2", content=[attachment("Binary/b2")])]

    assert await poll(harness) == 2

    notes = await _notes(practice.id)
    assert len(notes) == 2 and len({note.batch_id for note in notes}) == 1
    [run] = await runs(harness, practice)
    assert (run["pages"], run["accepted"]) == (2, 2)


async def test_the_same_pdf_under_another_document_is_recorded_as_a_duplicate(harness, ehr):
    practice = await connected(harness)
    one_note(ehr)
    ehr.documents.append(document("d2"))

    assert await poll(harness) == 1

    [note] = await _notes(practice.id)
    rows = {row["document_id"]: row for row in await documents(harness, practice)}
    assert (rows["d2"]["outcome"], rows["d2"]["note_id"]) == ("duplicate", note.id)
    [run] = await runs(harness, practice)
    assert (run["accepted"], run["duplicates"]) == (1, 1)


async def test_every_document_that_cannot_be_placed_is_recorded_with_its_reason(harness, ehr):
    practice = await connected(harness)
    visit(ehr)
    future = (TODAY + timedelta(days=3)).isoformat()
    ehr.honours_type = False
    ehr.resources["Encounter/e2"] = encounter("e2", f"{future}T09:00:00-06:00")
    ehr.resources["Practitioner/p9"] = practitioner("p9", STRANGER_NPI)
    ehr.binaries["Binary/b1"] = (NOTE_PDF, "application/pdf")
    ehr.documents += _unplaceable()

    assert await poll(harness) == 0

    reasons = {row["document_id"]: (row["outcome"], row["reason"]) for row in await documents(harness, practice)}
    assert reasons == {
        "d-preliminary": ("refused", "not_final"),
        "d-stranger": ("refused", "no_provider"),
        "d-undated": ("refused", "no_service_date"),
        "d-rtf": ("refused", "unsupported_format"),
        "d-empty": ("refused", "no_attachment"),
        "d-gone": ("refused", "attachment_unavailable"),
        "d-foreign": ("refused", "foreign_reference"),
        "d-future": ("refused", "future_service_date"),
        "d-altered": ("refused", "attachment_mismatch"),
        "d-huge": ("refused", "too_large"),
    }
    assert await _notes(practice.id) == []
    [run] = await runs(harness, practice)
    assert (run["outcome"], run["refused"], run["skipped"]) == ("succeeded", 10, 1)
    assert not any(request.url.host == "other.example.com" for request in ehr.requests)


async def test_an_html_note_is_rendered_to_pdf_and_an_emergency_visit_is_placed_in_the_er(harness, ehr):
    practice = await connected(harness)
    visit(ehr, class_code="EMER")
    ehr.binaries["Binary/h1"] = (EMERGENCY_NOTE, "text/html")
    ehr.documents.append(document("d1", content=[attachment("Binary/h1", "text/html; charset=utf-8")]))

    assert await poll(harness) == 1

    [note] = await _notes(practice.id)
    stored = harness.store.objects[note.file_key]
    assert note.place_code == "23"
    assert stored.startswith(b"%PDF")
    assert "Chest pain, troponin negative." in PdfReader(BytesIO(stored)).pages[0].extract_text()


async def test_an_attachment_sent_inline_is_read_without_another_request(harness, ehr):
    practice = await connected(harness)
    visit(ehr)
    inline = {"contentType": "application/pdf", "data": base64.b64encode(NOTE_PDF).decode()}
    ehr.documents.append(document("d1", content=[{"attachment": inline}]))

    assert await poll(harness) == 1

    [note] = await _notes(practice.id)
    assert harness.store.objects[note.file_key] == NOTE_PDF
    assert not any("/Binary/" in request.url.path for request in ehr.requests)


async def test_a_next_link_to_another_host_stops_the_run_and_keeps_the_cursor(harness, ehr):
    practice = await connected(harness)
    visit(ehr)
    ehr.page_size = 1
    ehr.foreign_next = "https://collector.example.net/fhir/r4/DocumentReference?page=1"
    ehr.binaries.update({"Binary/b1": (NOTE_PDF, "application/pdf"), "Binary/b2": (OTHER_PDF, "application/pdf")})
    ehr.documents += [document("d1"), document("d2", content=[attachment("Binary/b2")])]

    assert await poll(harness) == 1

    [run] = await runs(harness, practice)
    assert (run["outcome"], run["reason"], run["accepted"]) == ("failed", "foreign_link", 1)
    assert not any(request.url.host == "collector.example.net" for request in ehr.requests)
    async with SessionFactory() as db:
        assert await db.scalar(select(EhrPullRun.cursor)) is None


async def test_a_refused_token_or_a_server_asking_to_slow_down_fails_the_run_with_its_reason(harness, ehr):
    practice = await connected(harness)
    one_note(ehr)
    ehr.token_status = 401
    await poll(harness)
    ehr.token_status = 200
    slow_down = httpx.Response(429, headers={"retry-after": "900"})
    ehr.queued["/fhir/r4/DocumentReference"] = [slow_down]
    await pull_again(harness, practice, NOW + timedelta(minutes=20))

    assert [(run["outcome"], run["reason"]) for run in await runs(harness, practice)] == [
        ("failed", "rate_limited"),
        ("failed", "token_refused"),
    ]
    assert await _notes(practice.id) == []
    assert (await harness.client.get(API, headers=practice.admin)).json()["last_run"]["reason"] == "rate_limited"


async def test_only_due_connections_that_are_not_paused_are_pulled(harness, ehr):
    practice = await connected(harness)
    one_note(ehr)
    await harness.client.post(f"{API}/pause", headers=practice.admin)
    assert await poll(harness) == 0
    assert await runs(harness, practice) == []

    await harness.client.post(f"{API}/resume", headers=practice.admin)
    assert await poll(harness) == 1
    async with SessionFactory() as db:
        started = await db.scalar(select(EhrPullRun.created_at))
    await poll(harness, started + timedelta(minutes=5))
    assert len(await runs(harness, practice)) == 1
    await poll(harness, started + timedelta(minutes=16))
    assert len(await runs(harness, practice)) == 2


async def test_patient_details_never_reach_logs_keys_or_records(harness, ehr, caplog):
    practice = await connected(harness)
    one_note(ehr)
    caplog.set_level(logging.DEBUG)

    await poll(harness)

    assert "REYES" not in caplog.text and "patient-1" not in caplog.text
    assert not any("patient" in key.lower() or "reyes" in key.lower() for key in harness.store.objects)
    async with SessionFactory() as db:
        rows = (await db.execute(text("SELECT row_to_json(ehr_documents)::text FROM ehr_documents"))).scalars().all()
        runs_text = (await db.execute(text("SELECT row_to_json(ehr_pull_runs)::text FROM ehr_pull_runs"))).scalars()
        stored = " ".join([*rows, *runs_text.all()])
    assert "patient-1" not in stored and "REYES" not in stored
    assert practice.id in stored


async def test_documents_and_runs_cannot_be_changed_once_recorded(harness, ehr):
    await connected(harness)
    one_note(ehr)
    await poll(harness)

    for statement in (
        "UPDATE ehr_documents SET reason = 'no_place'",
        "DELETE FROM ehr_documents",
        "UPDATE ehr_pull_runs SET outcome = 'failed', reason = 'timeout'",
        "DELETE FROM ehr_pull_runs",
    ):
        async with SessionFactory() as db:
            with pytest.raises(DBAPIError):
                await db.execute(text(statement))
    async with SessionFactory() as db:
        assert await db.scalar(select(func.count()).select_from(EhrDocument)) == 1


async def test_purging_a_practice_removes_its_keys_connections_runs_and_documents(harness, ehr):
    practice = await connected(harness)
    one_note(ehr)
    await poll(harness)
    jwks_path = urlsplit(
        (await harness.client.get(API, headers=practice.admin)).json()["registration"]["jwks_url"]
    ).path
    hq = await sign_in(harness.client, "hq-admin@lakeside.example.com", secret_box=practice.secrets)
    path = f"/api/hq/practices/{practice.id}"
    await harness.client.patch(path, headers=hq, json={"status": "ended"})
    closed = await harness.client.post(f"{path}/close", headers=hq, json={"confirm_name": "Lakeside"})
    assert closed.status_code == 200, closed.text
    await backdate_closure(practice.id, 2558)

    purged = await harness.client.post(f"{path}/purge", headers=hq, json={"confirm_name": "Lakeside"})

    assert purged.status_code == 200, purged.text
    async with SessionFactory() as db:
        for table in (EhrKey, EhrConnection, EhrPullRun, EhrDocument):
            count = await db.scalar(select(func.count()).select_from(table).where(table.practice_id == practice.id))
            assert count == 0, table.__tablename__
    assert (await harness.client.get(jwks_path)).status_code == 404
