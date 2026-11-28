from app.codes.payer_rules import Payer
from tests.api.payer_helpers import add_payer, set_usual_payer
from tests.builders import practice_with_provider, read_next_note, reviewed_note, upload_note


async def _detail(harness, practice, note_id: str) -> dict:
    found = await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)
    assert found.status_code == 200, found.text
    return found.json()


async def _set_payer(harness, practice, note_id: str, payer: str | None) -> None:
    chosen = await harness.client.put(f"/api/notes/{note_id}/payer", headers=practice.admin, json={"payer": payer})
    assert chosen.status_code == 200, chosen.text


async def test_the_read_carries_the_payer_known_at_upload(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    medicare = await add_payer(harness, practice, "Medicare Part B", "medicare")
    await set_usual_payer(harness, practice, medicare)
    assert (await upload_note(harness, practice)).status_code == 200

    reviewer = await read_next_note(harness, icd_catalog)

    assert [inputs.payer for inputs in reviewer.calls] == [Payer("medicare")]
    note_id = (await harness.client.get("/api/notes", headers=practice.admin)).json()["items"][0]["id"]
    assert (await _detail(harness, practice, note_id))["analysis"]["payer_changed"] is False


async def test_a_payer_set_after_reading_offers_a_read_again_that_uses_it(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    medicare = await add_payer(harness, practice, "Medicare Part B", "medicare")
    assert (await _detail(harness, practice, note_id))["analysis"]["payer_changed"] is False

    await _set_payer(harness, practice, note_id, medicare)
    detail = await _detail(harness, practice, note_id)
    assert detail["analysis"]["payer_changed"] is True
    assert [(row["field"], row["new"]) for row in detail["history"]["changes"]] == [("payer", "Medicare Part B")]

    again = await harness.client.post(f"/api/notes/{note_id}/retry", headers=practice.admin)
    assert again.json() == {"status": "queued"}
    reviewer = await read_next_note(harness, icd_catalog)

    assert [inputs.payer for inputs in reviewer.calls] == [Payer("medicare")]
    detail = await _detail(harness, practice, note_id)
    assert [row["reason"] for row in detail["history"]["analyses"]] == ["upload", "payer"]
    assert detail["analysis"]["payer_changed"] is False


async def test_a_change_that_keeps_the_payer_guidance_offers_no_read_again(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    aetna = await add_payer(harness, practice, "Aetna", "commercial")
    medicaid = await add_payer(harness, practice, "Texas Medicaid", "medicaid")
    await set_usual_payer(harness, practice, aetna)
    await upload_note(harness, practice)
    await read_next_note(harness, icd_catalog)
    note_id = (await harness.client.get("/api/notes", headers=practice.admin)).json()["items"][0]["id"]

    await _set_payer(harness, practice, note_id, medicaid)

    assert (await _detail(harness, practice, note_id))["analysis"]["payer_changed"] is False
    refused = await harness.client.post(f"/api/notes/{note_id}/retry", headers=practice.admin)
    assert (refused.status_code, refused.json()["message"]) == (
        409,
        "the payer has not changed since this note was read",
    )


async def test_an_approved_note_is_not_read_again_for_its_payer(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    medicare = await add_payer(harness, practice, "Medicare Part B", "medicare")
    await _set_payer(harness, practice, note_id, medicare)
    assert (await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)).status_code == 200

    refused = await harness.client.post(f"/api/notes/{note_id}/retry", headers=practice.admin)

    assert (refused.status_code, refused.json()["message"]) == (409, "only notes that could not be read can be retried")
