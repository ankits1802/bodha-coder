from __future__ import annotations

from httpx import Response

from tests.builders import DOCUMENTED, Harness, Practice
from tests.fakes import signature_data_url

KEEP_I10 = {"choices": {"dx:I10": "keep"}}


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def decide(harness: Harness, practice: Practice, note_id: str, body: dict) -> Response:
    return await harness.client.put(f"/api/notes/{note_id}/decisions", headers=practice.admin, json=body)


async def keep_i10_with_reason(harness: Harness, practice: Practice, note_id: str) -> Response:
    return await decide(harness, practice, note_id, {**KEEP_I10, "reasons": {"dx:I10": DOCUMENTED}})


async def approve(harness: Harness, practice: Practice, note_id: str) -> Response:
    return await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)


async def provider_signature(harness: Harness, provider: dict[str, str], *, source: str = "typed") -> str:
    body = {"source": source, "typed_name": "Elena Varga", "image": signature_data_url()}
    drafted = await harness.client.post("/api/respond/signature/drafts", headers=provider, json=body)
    assert drafted.status_code == 200, drafted.text
    return drafted.json()["id"]


async def note_detail(harness: Harness, practice: Practice, note_id: str) -> dict:
    response = await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)
    assert response.status_code == 200, response.text
    return response.json()


async def access_rows(harness: Harness, practice: Practice) -> list[dict]:
    return (await harness.client.get("/api/access-log", headers=practice.admin)).json()["items"]


async def turn_on_level_confirmation(harness: Harness, practice: Practice, *, hold: bool) -> Response:
    return await harness.client.put(
        "/api/practice/review-settings",
        headers=practice.admin,
        json={"confirm_level_changes": True, "hold_until_confirmed": hold},
    )


async def provider_session(harness: Harness, link_token: str, *, wrong_first: bool = False) -> dict[str, str]:
    await harness.client.post("/api/respond/code", json={"token": link_token})
    code = harness.messenger.last_code()
    if wrong_first:
        wrong = "000000" if code != "000000" else "111111"
        refused = await harness.client.post("/api/respond/verify", json={"token": link_token, "code": wrong})
        assert refused.status_code == 401
    verified = await harness.client.post("/api/respond/verify", json={"token": link_token, "code": code})
    assert verified.status_code == 200, verified.text
    return bearer(verified.json()["provider_token"])
