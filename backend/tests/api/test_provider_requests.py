from sqlalchemy import update

from app.core.db import SessionFactory
from app.models import AddendumRequest
from tests.builders import practice_with_provider, read_next_note, upload_note
from tests.fakes import NOTE_TEXT

QUESTION = {"key": "dx:N18.30", "text": "What stage is the kidney disease?"}
MARISOL = "2026-11-25 - REYES MARISOL - 99215 - Progress.pdf"
JONAH = "2026-11-25 - PIKE JONAH - 99215 - Progress.pdf"


async def _note(harness, icd_catalog, practice, file_name: str) -> str:
    upload = await upload_note(harness, practice, file_name=file_name, body=f"{NOTE_TEXT} {file_name}")
    assert upload.status_code == 200, upload.text
    await read_next_note(harness, icd_catalog)
    listing = await harness.client.get(
        "/api/notes", headers=practice.admin, params={"batch_id": upload.json()["batch_id"]}
    )
    return listing.json()["items"][0]["id"]


async def _ask(harness, practice, note_id) -> tuple[str, str]:
    response = await harness.client.post(
        f"/api/notes/{note_id}/ask", headers=practice.admin, json={"questions": [QUESTION], "channel": "email"}
    )
    assert response.status_code == 200, response.text
    return response.json()["request_id"], harness.messenger.last_fragment()


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _provider_session(harness, link_token: str) -> dict[str, str]:
    await harness.client.post("/api/respond/code", json={"token": link_token})
    verified = await harness.client.post(
        "/api/respond/verify", json={"token": link_token, "code": harness.messenger.last_code()}
    )
    assert verified.status_code == 200, verified.text
    return _bearer(verified.json()["provider_token"])


async def _change_request(request_id: str, **values) -> None:
    async with SessionFactory() as db:
        await db.execute(update(AddendumRequest).where(AddendumRequest.id == request_id).values(**values))
        await db.commit()


async def _others(harness, provider) -> list[tuple[str, str, str, int]]:
    listing = await harness.client.get("/api/respond/others", headers=provider)
    assert listing.status_code == 200, listing.text
    return [(item["id"], item["patient_name"], item["service_date"], item["questions"]) for item in listing.json()]


async def _switch(harness, provider, request_id: str):
    return await harness.client.post("/api/respond/switch", headers=provider, json={"request_id": request_id})


async def test_after_signing_the_provider_moves_to_their_next_open_request(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    first = await _note(harness, icd_catalog, practice, MARISOL)
    second = await _note(harness, icd_catalog, practice, JONAH)
    first_id, first_link = await _ask(harness, practice, first)
    second_id, _ = await _ask(harness, practice, second)
    provider = await _provider_session(harness, first_link)

    assert await _others(harness, provider) == [(second_id, "Pike Jonah", "2026-11-25", 1)]
    signed = await harness.client.post(
        "/api/respond", headers=provider, json={"answers": [{"key": "dx:N18.30", "choice": "Yes"}], "confirmed": True}
    )
    assert signed.json()["status"] == "answered"
    assert await _others(harness, provider) == [(second_id, "Pike Jonah", "2026-11-25", 1)]

    switched = await _switch(harness, provider, second_id)
    assert switched.status_code == 200, switched.text
    next_session = _bearer(switched.json()["provider_token"])
    opened = (await harness.client.get("/api/respond", headers=next_session)).json()
    assert (opened["patient"]["name"], opened["status"]) == ("Pike Jonah", "sent")
    assert await _others(harness, next_session) == []
    assert (await _switch(harness, next_session, first_id)).status_code == 404

    log = (await harness.client.get("/api/access-log", headers=practice.admin)).json()["items"]
    assert ("provider", "switched request", second) in {(e["actor_kind"], e["action"], e["note_id"]) for e in log}


async def test_a_provider_cannot_switch_to_another_provider_s_request(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    first = await _note(harness, icd_catalog, practice, MARISOL)
    second = await _note(harness, icd_catalog, practice, JONAH)
    _, first_link = await _ask(harness, practice, first)
    second_id, _ = await _ask(harness, practice, second)
    colleague = await harness.client.post(
        "/api/providers",
        headers=practice.admin,
        json={"name": "Omar Haddad", "credential": "DO", "email": "haddad@clinic.example.com"},
    )
    assert colleague.status_code == 200, colleague.text
    await _change_request(second_id, provider_id=colleague.json()["id"])
    provider = await _provider_session(harness, first_link)

    assert await _others(harness, provider) == []
    assert (await _switch(harness, provider, second_id)).status_code == 404


async def test_a_provider_cannot_switch_to_a_request_of_another_practice(harness, icd_catalog):
    lakeside = await practice_with_provider(harness)
    hillside = await practice_with_provider(harness, name="Hillside", admin_email="admin@hillside.example.com")
    first = await _note(harness, icd_catalog, lakeside, MARISOL)
    elsewhere = await _note(harness, icd_catalog, hillside, JONAH)
    _, first_link = await _ask(harness, lakeside, first)
    elsewhere_id, _ = await _ask(harness, hillside, elsewhere)
    await _change_request(elsewhere_id, provider_id=lakeside.provider_id)
    provider = await _provider_session(harness, first_link)

    assert await _others(harness, provider) == []
    assert (await _switch(harness, provider, elsewhere_id)).status_code == 404


async def test_closed_requests_are_neither_listed_nor_opened(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    first = await _note(harness, icd_catalog, practice, MARISOL)
    second = await _note(harness, icd_catalog, practice, JONAH)
    _, first_link = await _ask(harness, practice, first)
    second_id, _ = await _ask(harness, practice, second)
    await _change_request(second_id, status="cancelled")
    provider = await _provider_session(harness, first_link)

    assert await _others(harness, provider) == []
    assert (await _switch(harness, provider, second_id)).status_code == 404
