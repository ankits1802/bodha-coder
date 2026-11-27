from datetime import timedelta

from sqlalchemy import update

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import AddendumRequest, utcnow
from app.services.reminders import send_due_reminders
from tests.builders import reviewed_note

PHONE = "+15555550142"
EMAIL = "varga@clinic.example.com"
MASKED_EMAIL = "va" + "•" * 20 + "om"
QUESTION = {"key": "dx:N18.30", "text": "What stage is the kidney disease?"}
TWILIO = {
    "twilio_account_sid": "AC00000000000000000000000000000000",
    "twilio_auth_token": "test-only",
    "twilio_from": "+18885550100",
}
NO_EMAIL = {"error": "invalid", "message": "Elena Varga has no email on file"}


def texts_on(monkeypatch) -> None:
    for name, value in {"app_environment": "production", "sms_transport": "twilio", **TWILIO}.items():
        monkeypatch.setattr(get_settings(), name, value)


def texts_off(monkeypatch) -> None:
    for name, value in {"app_environment": "production", "sms_transport": "outbox"}.items():
        monkeypatch.setattr(get_settings(), name, value)


async def _save_provider(harness, practice, **changes):
    body = {"name": "Elena Varga", "credential": "MD", "npi": "1234567893", "place_code": "11", "email": EMAIL}
    return await harness.client.put(
        f"/api/providers/{practice.provider_id}", headers=practice.admin, json={**body, **changes}
    )


async def _ask(harness, practice, note_id, channel: str):
    return await harness.client.post(
        f"/api/notes/{note_id}/ask", headers=practice.admin, json={"questions": [QUESTION], "channel": channel}
    )


async def _remind_now(messenger) -> int:
    async with SessionFactory() as db:
        await db.execute(update(AddendumRequest).values(remind_at=utcnow() - timedelta(minutes=1)))
        await db.commit()
    async with SessionFactory() as db:
        return await send_due_reminders(db, messenger)


async def test_asking_by_text_is_refused_while_texts_cannot_be_sent(harness, icd_catalog, monkeypatch):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    texts_off(monkeypatch)
    assert (await _save_provider(harness, practice, phone=PHONE)).status_code == 204

    refused = await _ask(harness, practice, note_id, "sms")

    assert refused.status_code == 409
    assert refused.json() == {"error": "conflict", "message": "text messages are not available; send by email"}
    assert PHONE not in [to for to, _ in harness.messenger.sent]
    detail = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()
    assert detail["requests"] == []


async def test_asking_by_text_reaches_the_phone_when_texts_are_set_up(harness, icd_catalog, monkeypatch):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    texts_on(monkeypatch)
    assert (await _save_provider(harness, practice, phone=PHONE)).status_code == 204

    assert (await _ask(harness, practice, note_id, "sms")).status_code == 200
    assert harness.messenger.sent[-1][0] == PHONE


async def test_a_text_request_moves_to_email_once_texts_stop(harness, icd_catalog, monkeypatch):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    texts_on(monkeypatch)
    await _save_provider(harness, practice, phone=PHONE)
    assert (await _ask(harness, practice, note_id, "sms")).status_code == 200
    token = harness.messenger.last_fragment()
    texts_off(monkeypatch)

    code = await harness.client.post("/api/respond/code", json={"token": token})
    assert code.status_code == 200
    assert (code.json()["sent_to"], harness.messenger.sent[-1][0]) == (MASKED_EMAIL, EMAIL)

    assert await _remind_now(harness.messenger) == 1
    to, body = harness.messenger.sent[-1]
    assert (to, body.startswith("Reminder: Lakeside has questions")) == (EMAIL, True)


async def test_a_text_request_without_an_email_is_held_once_texts_stop(harness, icd_catalog, monkeypatch):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    texts_on(monkeypatch)
    assert (await _save_provider(harness, practice, phone=PHONE, email=None)).status_code == 204
    assert (await _ask(harness, practice, note_id, "sms")).status_code == 200
    token = harness.messenger.last_fragment()
    texts_off(monkeypatch)
    sent_before = len(harness.messenger.sent)

    code = await harness.client.post("/api/respond/code", json={"token": token})
    assert (code.status_code, code.json()) == (422, NO_EMAIL)

    assert await _remind_now(harness.messenger) == 0
    assert len(harness.messenger.sent) == sent_before


async def test_a_provider_preferring_texts_is_saved_for_email_while_texts_cannot_be_sent(
    harness, icd_catalog, monkeypatch
):
    practice, _ = await reviewed_note(harness, icd_catalog)
    texts_off(monkeypatch)

    assert (await _save_provider(harness, practice, phone=PHONE, channel="sms")).status_code == 204

    providers = (await harness.client.get("/api/providers", headers=practice.admin)).json()
    assert [(row["channel"], row["phone"]) for row in providers] == [("email", PHONE)]


async def test_a_provider_with_only_a_phone_needs_texts_to_be_set_up(harness, icd_catalog, monkeypatch):
    practice, _ = await reviewed_note(harness, icd_catalog)
    texts_off(monkeypatch)

    refused = await _save_provider(harness, practice, phone=PHONE, email=None)
    assert (refused.status_code, refused.json()) == (422, NO_EMAIL)

    texts_on(monkeypatch)
    assert (await _save_provider(harness, practice, phone=PHONE, email=None)).status_code == 204
    providers = (await harness.client.get("/api/providers", headers=practice.admin)).json()
    assert [row["channel"] for row in providers] == ["sms"]


async def test_the_signed_in_practice_says_whether_texts_can_be_sent(harness, icd_catalog, monkeypatch):
    practice, _ = await reviewed_note(harness, icd_catalog)

    texts_off(monkeypatch)
    off = (await harness.client.get("/api/auth/me", headers=practice.admin)).json()
    texts_on(monkeypatch)
    on = (await harness.client.get("/api/auth/me", headers=practice.admin)).json()

    assert (off["practice"]["can_send_texts"], on["practice"]["can_send_texts"]) == (False, True)
