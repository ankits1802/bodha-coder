from tests.api.review_helpers import provider_signature
from tests.builders import reviewed_note

QUESTION = "What stage is the kidney disease?"


async def _ask(harness, practice, note_id):
    response = await harness.client.post(
        f"/api/notes/{note_id}/ask",
        headers=practice.admin,
        json={
            "questions": [{"key": "dx:N18.30", "text": QUESTION}],
            "channel": "email",
            "hold": True,
        },
    )
    assert response.status_code == 200, response.text
    return harness.messenger.last_fragment()


async def _provider_session(harness, token: str) -> dict[str, str]:
    sent = await harness.client.post("/api/respond/code", json={"token": token})
    assert sent.status_code == 200 and "@" not in sent.json()["sent_to"][2:-2]
    verified = await harness.client.post(
        "/api/respond/verify", json={"token": token, "code": harness.messenger.last_code()}
    )
    return {"Authorization": f"Bearer {verified.json()['provider_token']}"}


async def test_the_provider_answers_and_the_note_is_read_again(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    token = await _ask(harness, practice, note_id)
    assert harness.messenger.sent[-1][0] == "varga@clinic.example.com"
    assert (await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)).status_code == 409

    provider = await _provider_session(harness, token)
    request = (await harness.client.get("/api/respond", headers=provider)).json()
    assert request["questions"][0]["options"] == ["Yes", "No", "Clinically undetermined", "Other"]
    assert request["texts"][0]["source"] == "document"
    assert (request["place_name"], request["requested_by"]) == ("Office", "Practice Admin")

    answered = await harness.client.post(
        "/api/respond",
        headers=provider,
        json={
            "answers": [{"key": "dx:N18.30", "choice": "Yes"}],
            "confirmed": True,
            "signature_id": await provider_signature(harness, provider),
        },
    )
    assert answered.json()["status"] == "answered"
    assert f"{QUESTION} Yes." in answered.json()["addendum_text"]

    detail = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()
    assert [text["source"] for text in detail["texts"]] == ["document", "addendum"]
    assert [(a["revision"], a["reason"], a["status"]) for a in detail["history"]["analyses"]][-1] == (
        2,
        "addendum",
        "queued",
    )
    assert detail["note"]["status"] == "queued"


async def test_a_wrong_code_is_refused_and_attempts_are_limited(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    token = await _ask(harness, practice, note_id)
    await harness.client.post("/api/respond/code", json={"token": token})
    for _ in range(5):
        wrong = await harness.client.post("/api/respond/verify", json={"token": token, "code": "000000"})
        assert wrong.status_code == 401
    right = await harness.client.post(
        "/api/respond/verify", json={"token": token, "code": harness.messenger.last_code()}
    )
    assert right.status_code == 401


async def test_a_provider_token_opens_nothing_else(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    provider = await _provider_session(harness, await _ask(harness, practice, note_id))
    assert (await harness.client.get("/api/today", headers=provider)).status_code == 401


async def test_other_needs_the_provider_s_own_words(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    provider = await _provider_session(harness, await _ask(harness, practice, note_id))
    response = await harness.client.post(
        "/api/respond",
        headers=provider,
        json={
            "answers": [{"key": "dx:N18.30", "choice": "Other"}],
            "confirmed": True,
        },
    )
    assert response.status_code == 422
