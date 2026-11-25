from datetime import timedelta

from sqlalchemy import update

from app.core.db import SessionFactory
from app.models import AddendumRequest, utcnow
from app.services.reminders import expire_requests, send_due_reminders
from tests.builders import reviewed_note


async def _ask(harness, practice, note_id) -> str:
    response = await harness.client.post(
        f"/api/notes/{note_id}/ask",
        headers=practice.admin,
        json={"questions": [{"key": "dx:N18.30", "text": "What stage is the kidney disease?"}], "channel": "email"},
    )
    assert response.status_code == 200, response.text
    return harness.messenger.last_fragment()


async def _set_on_requests(**values) -> None:
    async with SessionFactory() as db:
        await db.execute(update(AddendumRequest).values(**values))
        await db.commit()


async def test_an_unanswered_request_is_reminded_once_with_a_fresh_link(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    first_link = await _ask(harness, practice, note_id)
    await _set_on_requests(remind_at=utcnow() - timedelta(minutes=1))

    async with SessionFactory() as db:
        assert await send_due_reminders(db, harness.messenger) == 1
    to, body = harness.messenger.sent[-1]
    assert (to, body.startswith("Reminder: Lakeside has questions")) == ("varga@clinic.example.com", True)
    fresh_link = harness.messenger.last_fragment()
    assert fresh_link != first_link
    assert (await harness.client.post("/api/respond/code", json={"token": first_link})).status_code == 404
    assert (await harness.client.post("/api/respond/code", json={"token": fresh_link})).status_code == 200

    async with SessionFactory() as db:
        assert await send_due_reminders(db, harness.messenger) == 0


async def test_an_expired_request_hands_the_note_back_and_releases_the_claim(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await _ask(harness, practice, note_id)
    assert (await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)).status_code == 409
    await _set_on_requests(expires_at=utcnow() - timedelta(minutes=1))

    async with SessionFactory() as db:
        assert await expire_requests(db) == 1
    detail = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()
    assert detail["requests"][0]["status"] == "expired"
    assert (detail["note"]["lane"], detail["note"]["lane_reason"]) == ("coder", "code_changes")
    assert (await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)).status_code == 200
