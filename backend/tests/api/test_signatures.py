import hashlib

from sqlalchemy import select

from app.ai.errors import ModelUnavailable
from app.core.db import SessionFactory
from app.models import Signature, SignatureAdoption
from tests.builders import invite_member, practice_with_member, sign_in
from tests.fakes import signature_data_url, signature_png

CODER = "cora@lakeside.example.com"


def draft(source: str = "drawn", **changes) -> dict:
    return {"source": source, "typed_name": "Cora Coder", "image": signature_data_url(), **changes}


async def _coder(harness):
    practice = await practice_with_member(harness, name="Cora Coder", email=CODER, role="coder")
    return practice, await sign_in(harness.client, CODER, secret_box=practice.secrets)


async def _signatures(user_id: str) -> list[Signature]:
    async with SessionFactory() as db:
        rows = await db.scalars(select(Signature).where(Signature.user_id == user_id).order_by(Signature.created_at))
        return list(rows.all())


async def test_a_drawn_signature_is_checked_stored_by_id_and_previewed(harness):
    _, coder = await _coder(harness)

    drafted = await harness.client.post("/api/signature/drafts", headers=coder, json=draft())

    assert drafted.status_code == 200, drafted.text
    body = drafted.json()
    assert (body["source"], body["typed_name"], body["image"]) == ("drawn", "Cora Coder", signature_data_url())
    [row] = await _signatures((await _me(harness, coder))["id"])
    assert row.file_key == f"people/{row.user_id}/signatures/{row.id}.png"
    assert harness.store.objects[row.file_key] == signature_png()
    assert row.sha256 == hashlib.sha256(signature_png()).hexdigest()
    assert (row.checked, row.check["model"], row.check["is_signature"]) == (True, "fake-gemini", True)
    assert (row.width, row.height, row.ip) == (120, 48, "127.0.0.1")
    assert harness.image_model.images == [signature_png()]
    assert (await harness.client.get("/api/signature", headers=coder)).json() == {"signature": None}


async def test_an_image_the_check_says_is_not_a_signature_is_refused_and_not_kept(harness):
    _, coder = await _coder(harness)
    harness.image_model.answer["is_signature"] = False
    before = set(harness.store.objects)

    refused = await harness.client.post("/api/signature/drafts", headers=coder, json=draft("uploaded"))

    assert refused.status_code == 422
    assert "handwritten signature" in refused.json()["message"]
    assert set(harness.store.objects) == before
    assert await _signatures((await _me(harness, coder))["id"]) == []


async def test_a_typed_signature_needs_no_image_check(harness):
    _, coder = await _coder(harness)
    harness.image_model.answer["is_signature"] = False

    drafted = await harness.client.post("/api/signature/drafts", headers=coder, json=draft("typed"))

    assert drafted.status_code == 200, drafted.text
    assert harness.image_model.images == []
    [row] = await _signatures((await _me(harness, coder))["id"])
    assert (row.source, row.checked, row.check) == ("typed", False, None)


async def test_without_the_check_a_drawn_signature_waits_and_typing_still_works(harness):
    _, coder = await _coder(harness)
    harness.image_model.failure = ModelUnavailable("down")

    drawn = await harness.client.post("/api/signature/drafts", headers=coder, json=draft("drawn"))
    typed = await harness.client.post("/api/signature/drafts", headers=coder, json=draft("typed"))

    assert drawn.status_code == 503 and "type your name" in drawn.json()["message"]
    assert typed.status_code == 200


async def test_only_a_png_data_url_of_a_sensible_size_is_accepted(harness):
    _, coder = await _coder(harness)
    path = "/api/signature/drafts"

    jpeg = await harness.client.post(path, headers=coder, json=draft(image="data:image/jpeg;base64,AAAA"))
    tiny = await harness.client.post(path, headers=coder, json=draft(image=signature_data_url(signature_png(10, 10))))
    broken = await harness.client.post(path, headers=coder, json=draft(image="data:image/png;base64,iVBORw0KGgo="))

    assert (jpeg.status_code, tiny.status_code, broken.status_code) == (422, 422, 422)


async def test_adopting_and_replacing_keeps_every_signature_as_a_record(harness):
    _, coder = await _coder(harness)
    first = (await harness.client.post("/api/signature/drafts", headers=coder, json=draft("typed"))).json()
    second = (await harness.client.post("/api/signature/drafts", headers=coder, json=draft("drawn"))).json()

    adopted = await harness.client.post(f"/api/signature/drafts/{first['id']}/adopt", headers=coder)
    replaced = await harness.client.post(f"/api/signature/drafts/{second['id']}/adopt", headers=coder)

    assert adopted.json()["signature"]["id"] == first["id"]
    assert replaced.json()["signature"]["id"] == second["id"]
    assert (await harness.client.get("/api/signature", headers=coder)).json()["signature"]["id"] == second["id"]
    user_id = (await _me(harness, coder))["id"]
    assert [row.id for row in await _signatures(user_id)] == [first["id"], second["id"]]
    async with SessionFactory() as db:
        adoptions = (
            await db.scalars(select(SignatureAdoption.signature_id).order_by(SignatureAdoption.created_at))
        ).all()
    assert list(adoptions)[-2:] == [first["id"], second["id"]]


async def test_nobody_can_adopt_another_person_s_signature(harness):
    practice, coder = await _coder(harness)
    await invite_member(harness, practice, name="Dee Cdi", email="dee@lakeside.example.com", role="cdi")
    cdi = await sign_in(harness.client, "dee@lakeside.example.com", secret_box=practice.secrets)
    theirs = (await harness.client.post("/api/signature/drafts", headers=coder, json=draft("typed"))).json()

    taken = await harness.client.post(f"/api/signature/drafts/{theirs['id']}/adopt", headers=cdi)

    assert taken.status_code == 404
    assert (await harness.client.get("/api/signature", headers=cdi)).json() == {"signature": None}


async def test_drafts_are_rate_limited_per_person(harness):
    _, coder = await _coder(harness)
    answers = [
        (await harness.client.post("/api/signature/drafts", headers=coder, json=draft("typed"))).status_code
        for _ in range(21)
    ]
    assert answers[:20] == [200] * 20 and answers[20] == 429


async def test_billers_have_no_signature_to_capture(harness):
    practice = await practice_with_member(harness, name="Bo Biller", email="bo@lakeside.example.com", role="biller")
    biller = await sign_in(harness.client, "bo@lakeside.example.com", secret_box=practice.secrets)
    assert (await harness.client.post("/api/signature/drafts", headers=biller, json=draft("typed"))).status_code == 403


async def _me(harness, headers) -> dict:
    response = await harness.client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()
