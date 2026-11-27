from datetime import UTC, datetime

from sqlalchemy import update

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import Practice
from app.services.digests import send_due_digests
from tests.builders import invite_member, reviewed_note

HALF_PAST_SIX_IN_CHICAGO = datetime(2026, 11, 27, 12, 30, tzinfo=UTC)
HALF_PAST_SEVEN_IN_CHICAGO = datetime(2026, 11, 27, 13, 30, tzinfo=UTC)
NEXT_MORNING_IN_CHICAGO = datetime(2026, 11, 28, 13, 30, tzinfo=UTC)
ADMIN = "admin@lakeside.example.com"
CODER = "priya@lakeside.example.com"


async def _digests(harness, now: datetime) -> dict[str, str]:
    before = len(harness.messenger.sent)
    async with SessionFactory() as db:
        count = await send_due_digests(db, harness.messenger, now)
    sent = harness.messenger.sent[before:]
    assert count == len(sent)
    return dict(sent)


async def test_the_summary_waits_for_seven_in_the_practice_time_zone(harness, icd_catalog):
    practice, _ = await reviewed_note(harness, icd_catalog)
    assert await _digests(harness, HALF_PAST_SIX_IN_CHICAGO) == {}

    async with SessionFactory() as db:
        await db.execute(update(Practice).where(Practice.id == practice.id).values(time_zone="America/New_York"))
        await db.commit()
    assert list(await _digests(harness, HALF_PAST_SIX_IN_CHICAGO)) == [ADMIN]


async def test_each_reader_gets_counts_and_a_link_once_a_practice_day(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    coder_id = await invite_member(harness, practice, name="Priya Nair", email=CODER, role="coder")
    await invite_member(harness, practice, name="Sam Okafor", email="sam@lakeside.example.com", role="viewer")
    assigned = await harness.client.post(
        "/api/notes/assign", headers=practice.admin, json={"note_ids": [note_id], "user_id": coder_id}
    )
    assert assigned.status_code == 200, assigned.text

    sent = await _digests(harness, HALF_PAST_SEVEN_IN_CHICAGO)
    assert sorted(sent) == [ADMIN, CODER]
    assert sent[CODER].splitlines() == [
        "Lakeside, Friday 27 November 2026",
        "",
        "Waiting for review: 1",
        "Ready to approve: 0",
        "Needs a coder: 1",
        "Waiting on provider: 0",
        "Compliance: 0",
        "Due within 24 hours: 1",
        "Assigned to you: 1",
        "",
        f"Open Today: {get_settings().app_url}/today",
    ]
    assert "Assigned to you: 0" in sent[ADMIN].splitlines()
    assert not any(word in body for body in sent.values() for word in ("Marisol", "REYES", "99215", "Varga"))

    assert await _digests(harness, HALF_PAST_SEVEN_IN_CHICAGO) == {}
    assert sorted(await _digests(harness, NEXT_MORNING_IN_CHICAGO)) == [ADMIN, CODER]


async def test_a_reader_can_turn_the_summary_off(harness, icd_catalog):
    practice, _ = await reviewed_note(harness, icd_catalog)
    preferences = await harness.client.get("/api/auth/preferences", headers=practice.admin)
    assert preferences.json() == {"notify_digest": True}

    saved = await harness.client.put("/api/auth/preferences", headers=practice.admin, json={"notify_digest": False})
    assert saved.json() == {"notify_digest": False}
    assert (await harness.client.get("/api/auth/preferences", headers=practice.admin)).json() == {
        "notify_digest": False
    }
    assert await _digests(harness, HALF_PAST_SEVEN_IN_CHICAGO) == {}
