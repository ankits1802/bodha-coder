from __future__ import annotations

import asyncio
import secrets
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.db import SessionFactory
from app.core.errors import Conflict
from app.models import AccessLog, Activity, AddendumRequest, Note, NoteText, User, utcnow
from app.services.query_governance import escalate_unanswered, refuse_repeat_queries, repeat_query_blocked
from app.services.query_metrics import AskedRequest, metrics_for
from tests.builders import reviewed_note

ADMIN = "admin@lakeside.example.com"
OPTIONS = ["Yes", "No", "Clinically undetermined", "Other"]
SIGNED_TEXT = "Addendum by Elena Varga, MD, 26 Nov 2026.\nWhat stage is the kidney disease? Stage 3b."


async def _add_request(
    note_id: str,
    *,
    keys: tuple[str, ...],
    sent_at: datetime,
    status: str = "sent",
    answered_at: datetime | None = None,
    choices: tuple[str, ...] = (),
    escalated_at: datetime | None = None,
) -> str:
    async with SessionFactory() as db:
        note = await db.get_one(Note, note_id)
        admin = await db.scalar(select(User.id).where(User.email == ADMIN))
        request = AddendumRequest(
            practice_id=note.practice_id,
            note_id=note.id,
            analysis_id=note.current_analysis_id,
            provider_id=note.provider_id,
            questions=[{"key": key, "text": f"Question {key}", "context": [], "options": OPTIONS} for key in keys],
            answers=[{"key": key, "choice": choice, "comment": None} for key, choice in zip(keys, choices, strict=True)]
            if choices
            else None,
            addendum_text=SIGNED_TEXT if status == "answered" else None,
            channel="email",
            token_hash=secrets.token_hex(32),
            expires_at=sent_at + timedelta(hours=72),
            hold_claim=False,
            status=status,
            sent_by=admin,
            created_at=sent_at,
            answered_at=answered_at,
            escalated_at=escalated_at,
        )
        db.add(request)
        await db.commit()
        return request.id


async def _add_text(note_id: str, revision: int, *, source: str, request_id: str | None = None) -> None:
    async with SessionFactory() as db:
        db.add(
            NoteText(note_id=note_id, revision=revision, source=source, text="More.", addendum_request_id=request_id)
        )
        await db.commit()


async def _blocked(note_id: str, keys: list[str]) -> list[str]:
    async with SessionFactory() as db:
        return await repeat_query_blocked(db, await db.get_one(Note, note_id), keys)


async def test_a_question_asked_before_is_blocked_until_the_note_has_new_text(harness, icd_catalog):
    _, note_id = await reviewed_note(harness, icd_catalog)
    asked = await _add_request(
        note_id,
        keys=("dx:N18.30",),
        sent_at=utcnow(),
        status="answered",
        answered_at=utcnow(),
        choices=("Clinically undetermined",),
    )
    await _add_request(note_id, keys=("em",), sent_at=utcnow(), status="cancelled")
    assert await _blocked(note_id, ["em", "dx:N18.30", "dx:N18.30"]) == ["dx:N18.30"]

    await _add_text(note_id, 2, source="addendum", request_id=asked)
    assert await _blocked(note_id, ["dx:N18.30"]) == ["dx:N18.30"]
    async with SessionFactory() as db:
        with pytest.raises(Conflict) as refused:
            await refuse_repeat_queries(db, await db.get_one(Note, note_id), ["dx:N18.30"])
    assert refused.value.message.endswith("since: dx:N18.30")

    await _add_text(note_id, 3, source="document")
    assert await _blocked(note_id, ["dx:N18.30"]) == []


async def test_query_metrics_per_provider_over_http(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    sent = utcnow() - timedelta(hours=10)
    await _add_request(
        note_id,
        keys=("dx:N18.30", "em"),
        sent_at=sent,
        status="answered",
        answered_at=sent + timedelta(hours=3),
        choices=("Yes", "No"),
    )
    await _add_request(note_id, keys=("dx:N18.30",), sent_at=sent + timedelta(hours=5))

    response = await harness.client.get("/api/insights/queries", headers=practice.admin, params={"days": "30"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["days"] == 30
    assert body["providers"] == [
        {
            "provider_id": practice.provider_id,
            "provider_name": "Elena Varga",
            "notes": 1,
            "queries": 3,
            "per_100_notes": 300.0,
            "response_rate": 0.6667,
            "median_hours": 3.0,
            "agree_rate": 0.5,
            "repeat_rate": 0.3333,
        }
    ]
    assert body["total"]["queries"] == 3
    refused = await harness.client.get("/api/insights/queries", headers=practice.admin, params={"days": "8"})
    assert refused.status_code == 422


def test_query_metrics_from_hand_counted_requests():
    start = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
    requests = [
        AskedRequest(
            "p1", "n1", start, start + timedelta(hours=2), ("k1", "k2"), ("Yes", "Clinically undetermined"), 0
        ),
        AskedRequest("p1", "n2", start, start + timedelta(hours=6), ("k3",), ("Stage 3b",), 0),
        AskedRequest("p1", "n1", start + timedelta(days=1), None, ("k1",), (), 1),
    ]

    found = metrics_for(4, requests)

    assert (found.notes, found.queries, found.per_100_notes) == (4, 4, 100.0)
    assert (found.response_rate, found.median_hours, found.agree_rate, found.repeat_rate) == (0.75, 4.0, 0.6667, 0.25)
    empty = metrics_for(0, [])
    assert (empty.per_100_notes, empty.response_rate, empty.median_hours, empty.agree_rate) == (None, None, None, None)


async def test_requests_unanswered_for_48_hours_are_escalated_once_without_patient_details(harness, icd_catalog):
    _, note_id = await reviewed_note(harness, icd_catalog)
    now = utcnow()
    late = await _add_request(note_id, keys=("dx:N18.30",), sent_at=now - timedelta(hours=49))
    await _add_request(note_id, keys=("em",), sent_at=now - timedelta(hours=10))
    await _add_request(note_id, keys=("em",), sent_at=now - timedelta(hours=50), escalated_at=now - timedelta(hours=1))
    await _add_request(
        note_id,
        keys=("hcc:E11.65",),
        sent_at=now - timedelta(hours=60),
        status="answered",
        answered_at=now - timedelta(hours=55),
        choices=("Yes",),
    )
    before = len(harness.messenger.sent)

    async with SessionFactory() as db:
        assert await escalate_unanswered(db, harness.messenger, now) == 1

    sent = harness.messenger.sent[before:]
    assert [to for to, _ in sent] == [ADMIN]
    body = sent[0][1]
    assert "Lakeside: 1 provider question request has had no answer for more than 48 hours." in body
    assert "Reyes" not in body and "Marisol" not in body and "N18" not in body
    async with SessionFactory() as db:
        assert (await db.get_one(AddendumRequest, late)).escalated_at == now
        recorded = await db.scalar(select(Activity.detail).where(Activity.action == "provider requests escalated"))
        assert recorded == "1 requests, 1 admins"
        assert await escalate_unanswered(db, harness.messenger, now) == 0
    assert len(harness.messenger.sent) == before + 1


async def test_two_workers_escalating_at_once_send_one_message(harness, icd_catalog):
    _, note_id = await reviewed_note(harness, icd_catalog)
    now = utcnow()
    await _add_request(note_id, keys=("dx:N18.30",), sent_at=now - timedelta(hours=49))
    before = len(harness.messenger.sent)

    async def escalate() -> int:
        async with SessionFactory() as db:
            return await escalate_unanswered(db, harness.messenger, now)

    assert sum(await asyncio.gather(escalate(), escalate())) == 1
    assert len(harness.messenger.sent) == before + 1


async def test_the_signed_addendum_exports_with_its_label(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    missing = await harness.client.get(f"/api/notes/{note_id}/addendum.txt", headers=practice.admin)
    assert missing.status_code == 404
    signed = datetime(2026, 11, 27, 3, 0, tzinfo=UTC)
    await _add_request(
        note_id,
        keys=("dx:N18.30",),
        sent_at=signed - timedelta(hours=8),
        status="answered",
        answered_at=signed,
        choices=("Yes",),
    )

    response = await harness.client.get(f"/api/notes/{note_id}/addendum.txt", headers=practice.admin)

    assert response.status_code == 200, response.text
    assert response.headers["content-disposition"] == f'attachment; filename="addendum-{note_id}.txt"'
    assert response.text == (
        "ADDENDUM — dated 26 Nov 2026 — signed by Elena Varga, MD — refers to the visit of 25 Nov 2026\n\n"
        f"{SIGNED_TEXT}\n"
    )
    async with SessionFactory() as db:
        logged = await db.scalar(select(AccessLog.note_id).where(AccessLog.action == "exported addendum"))
    assert logged == note_id
