from app.ai.errors import ModelRequestRejected
from app.core.config import get_settings
from app.worker import process_one
from tests.builders import analysis_deps, practice_with_provider, sign_in, upload_note
from tests.fakes import FailingReviewer

REASON = "The Gemini account has no credits left (HTTP 402)."


async def _fail_next_read(harness, icd_catalog) -> None:
    deps = analysis_deps(harness, icd_catalog, FailingReviewer(ModelRequestRejected(REASON, status=402)))
    assert await process_one(deps, get_settings()) is True


async def test_a_note_that_could_not_be_read_says_why_and_can_be_read_again(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    await upload_note(harness, practice)
    await _fail_next_read(harness, icd_catalog)

    page = (await harness.client.get("/api/notes", headers=practice.admin)).json()
    assert (page["total"], page["all_total"], page["failed"]) == (1, 1, 1)
    note_id = page["items"][0]["id"]
    assert page["items"][0]["status"] == "failed"

    detail = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()
    assert (detail["note"]["status"], detail["failure"]) == ("failed", REASON)

    retried = await harness.client.post("/api/notes/retry", headers=practice.admin, json={})
    assert retried.json() == {"queued": [note_id]}
    again = (await harness.client.get("/api/notes", headers=practice.admin)).json()
    assert (again["failed"], again["items"][0]["status"]) == (0, "queued")


async def test_hq_sees_which_practice_could_not_be_read_and_why(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    await upload_note(harness, practice)
    await _fail_next_read(harness, icd_catalog)
    hq = await sign_in(harness.client, "hq-admin@lakeside.example.com", secret_box=practice.secrets)

    row = (await harness.client.get("/api/hq/practices", headers=hq)).json()[0]
    assert (row["failed_24h"], row["last_failure"]) == (1, REASON)
