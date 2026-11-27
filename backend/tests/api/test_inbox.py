from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import update

from app.adapters.billing_contract import PAYMENT_FAILED
from app.core.db import SessionFactory
from app.models import AddendumRequest, Practice, Subscription, utcnow
from app.services.plan_notices import notify_plans_ending
from app.services.reminders import expire_requests
from tests.api.billing_helpers import configure_prices, practice_on_plan, send_event, stripe_state
from tests.api.inbox_helpers import CODER_EMAIL, ask_provider, entries, inbox_of, stored_items
from tests.api.review_helpers import (
    approve,
    keep_i10_with_reason,
    provider_session,
    provider_signature,
    turn_on_level_confirmation,
)
from tests.api.test_quality_samples import audit_setup
from tests.builders import invite_member, practice_with_provider, reviewed_note, sign_in

CHICAGO = ZoneInfo("America/Chicago")
VARGA = "Elena Varga"
ADMIN_NAME = "Practice Admin"


async def test_a_signed_addendum_tells_the_person_who_asked_and_nobody_else(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await invite_member(harness, practice, name="Cora Coder", email=CODER_EMAIL, role="coder")
    coder = await sign_in(harness.client, CODER_EMAIL)
    provider = await provider_session(harness, await ask_provider(harness, coder, note_id))

    signed = await harness.client.post(
        "/api/respond",
        headers=provider,
        json={
            "answers": [{"key": "dx:N18.30", "choice": "Yes"}],
            "confirmed": True,
            "signature_id": await provider_signature(harness, provider),
        },
    )

    assert signed.status_code == 200, signed.text
    page = await inbox_of(harness, coder)
    assert entries(page) == [("provider_answered", VARGA, note_id, {"questions": 1})]
    item = page["items"][0]
    assert (item["patient_name"], item["service_date"], item["read_at"], page["unread"]) == (
        "Reyes Marisol",
        "2026-11-25",
        None,
        1,
    )
    assert (await inbox_of(harness, practice.admin))["items"] == []
    assert [row.payload for row in await stored_items()] == [{"questions": 1}]


async def test_an_expired_request_tells_the_person_who_asked(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await ask_provider(harness, practice.admin, note_id)
    async with SessionFactory() as db:
        await db.execute(update(AddendumRequest).values(expires_at=utcnow() - timedelta(minutes=1)))
        await db.commit()

    async with SessionFactory() as db:
        assert await expire_requests(db) == 1

    page = await inbox_of(harness, practice.admin)
    assert entries(page) == [("request_expired", "Bodha", note_id, {"purpose": "questions"})]


async def test_a_level_disagreement_tells_the_approver_and_still_emails_them(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    assert (await turn_on_level_confirmation(harness, practice, hold=False)).status_code == 200
    await keep_i10_with_reason(harness, practice, note_id)
    assert (await approve(harness, practice, note_id)).status_code == 200
    provider = await provider_session(harness, harness.messenger.last_fragment())

    disagreed = await harness.client.post(
        "/api/respond/level-change",
        headers=provider,
        json={
            "answer": "disagree",
            "comment": "Time supports 99215.",
            "confirmed": True,
            "signature_id": await provider_signature(harness, provider),
        },
    )

    assert disagreed.status_code == 200, disagreed.text
    assert entries(await inbox_of(harness, practice.admin)) == [("level_disagreed", VARGA, note_id, {})]
    assert harness.messenger.sent[-1][0] == "admin@lakeside.example.com"
    assert [row.payload for row in await stored_items()] == [{}]


async def test_a_mention_lands_in_the_inbox_of_the_person_named_and_still_emails_them(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    coder_id = await invite_member(harness, practice, name="Cora Coder", email=CODER_EMAIL, role="coder")
    coder = await sign_in(harness.client, CODER_EMAIL)

    posted = await harness.client.post(
        f"/api/notes/{note_id}/comments",
        headers=practice.admin,
        json={"finding_key": "em", "body": "Reyes chart: please look", "mentions": [coder_id]},
    )

    assert posted.status_code == 200, posted.text
    comment_id = posted.json()["id"]
    assert entries(await inbox_of(harness, coder)) == [
        ("mentioned", ADMIN_NAME, note_id, {"comment_id": comment_id, "on": "finding"})
    ]
    assert (await inbox_of(harness, practice.admin))["items"] == []
    assert harness.messenger.sent[-1][0] == CODER_EMAIL
    assert "Reyes" not in str([row.payload for row in await stored_items()])


async def test_assigning_training_tells_the_trainee_without_naming_any_note(harness, icd_catalog):
    _, coder, run_id, notes = await audit_setup(harness, icd_catalog, purpose="training")

    page = await inbox_of(harness, coder)

    assert entries(page) == [("training_assigned", ADMIN_NAME, None, {"run_id": run_id, "notes": len(notes)})]
    assert (page["items"][0]["patient_name"], page["items"][0]["service_date"]) == (None, None)


async def test_a_blind_audit_draw_writes_nothing_to_the_inbox(harness, icd_catalog):
    await audit_setup(harness, icd_catalog, purpose="audit")

    assert await stored_items() == []


async def test_a_failed_payment_tells_every_active_admin_once(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_on_plan(harness, "trial")
    await send_event(harness, "evt_1", stripe_state(practice.id))
    assert (await inbox_of(harness, practice.admin))["items"] == []

    await send_event(harness, "evt_2", stripe_state(practice.id), payment=PAYMENT_FAILED)
    await send_event(harness, "evt_3", stripe_state(practice.id), payment=PAYMENT_FAILED)

    async with SessionFactory() as db:
        last_day = (await db.get_one(Practice, practice.id)).renews_on
    assert last_day is not None
    page = await inbox_of(harness, practice.admin)
    assert entries(page) == [("payment_failed", "Bodha", None, {"access_until": last_day.isoformat()})]


async def test_a_plan_ending_within_three_days_tells_the_admins_once(harness):
    practice = await practice_with_provider(harness)
    today = datetime.now(CHICAGO).date()
    await _renews_on(practice.id, today + timedelta(days=4))
    async with SessionFactory() as db:
        assert await notify_plans_ending(db, utcnow()) == 0

    await _renews_on(practice.id, today + timedelta(days=2))
    async with SessionFactory() as db:
        assert await notify_plans_ending(db, utcnow()) == 1
    async with SessionFactory() as db:
        assert await notify_plans_ending(db, utcnow()) == 0

    ends_on = (today + timedelta(days=2)).isoformat()
    assert entries(await inbox_of(harness, practice.admin)) == [("plan_ending", "Bodha", None, {"ends_on": ends_on})]


async def test_a_live_subscription_is_not_told_its_plan_is_ending(harness):
    practice = await practice_with_provider(harness)
    await _renews_on(practice.id, datetime.now(CHICAGO).date() + timedelta(days=1))
    async with SessionFactory() as db:
        db.add(
            Subscription(
                practice_id=practice.id,
                provider="stripe",
                subscription_id="sub_1",
                plan="professional",
                interval="monthly",
                status="active",
            )
        )
        await db.commit()

    async with SessionFactory() as db:
        assert await notify_plans_ending(db, utcnow()) == 0


async def _renews_on(practice_id: str, day) -> None:
    async with SessionFactory() as db:
        await db.execute(update(Practice).where(Practice.id == practice_id).values(renews_on=day))
        await db.commit()
