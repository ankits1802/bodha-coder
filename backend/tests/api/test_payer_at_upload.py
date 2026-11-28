from tests.api.payer_helpers import add_payer, payers_by_file, set_usual_payer, upload_with_payers
from tests.batches import lines_pdf
from tests.builders import practice_with_provider


async def test_each_file_keeps_its_own_payer_and_the_others_take_the_batch_payer(harness):
    practice = await practice_with_provider(harness)
    medicare = await add_payer(harness, practice, "Medicare Part B", "medicare")
    aetna = await add_payer(harness, practice, "Aetna", "commercial")
    details = [{"billed": "99214", "payer": medicare}, {"billed": "99213"}, {"billed": "99212", "payer": None}]

    uploaded = await upload_with_payers(harness, practice, details, batch_payer=aetna)

    assert uploaded.status_code == 200, uploaded.text
    assert await payers_by_file(harness, practice) == {
        "visit-0.pdf": medicare,
        "visit-1.pdf": aetna,
        "visit-2.pdf": None,
    }


async def test_an_upload_without_any_payer_is_read_as_before(harness):
    practice = await practice_with_provider(harness)
    await add_payer(harness, practice, "Medicare Part B", "medicare")

    uploaded = await upload_with_payers(harness, practice, [{"billed": "99214"}])

    assert uploaded.status_code == 200, uploaded.text
    assert await payers_by_file(harness, practice) == {"visit-0.pdf": None}


async def test_the_providers_usual_payer_is_used_when_none_is_chosen_but_an_explicit_none_is_kept(harness):
    practice = await practice_with_provider(harness)
    medicare = await add_payer(harness, practice, "Medicare Part B", "medicare")
    aetna = await add_payer(harness, practice, "Aetna", "commercial")
    assert (await set_usual_payer(harness, practice, medicare)).status_code == 204
    details = [{"billed": "99214"}, {"billed": "99213", "payer": None}, {"billed": "99212", "payer": aetna}]

    uploaded = await upload_with_payers(harness, practice, details)

    assert uploaded.status_code == 200, uploaded.text
    assert await payers_by_file(harness, practice) == {
        "visit-0.pdf": medicare,
        "visit-1.pdf": None,
        "visit-2.pdf": aetna,
    }


async def test_a_payer_that_is_not_active_in_the_list_stops_the_upload(harness):
    practice = await practice_with_provider(harness)
    retired = await add_payer(harness, practice, "Old plan", "commercial", active=False)

    for payer in (retired, "not-a-payer"):
        refused = await upload_with_payers(harness, practice, [{"billed": "99214", "payer": payer}])
        assert (refused.status_code, refused.json()["message"]) == (422, "visit-0.pdf: choose an active payer")
    assert await payers_by_file(harness, practice) == {}


async def test_the_usual_payer_is_an_active_payer_and_leaves_with_it(harness):
    practice = await practice_with_provider(harness)
    medicare = await add_payer(harness, practice, "Medicare Part B", "medicare")
    retired = await add_payer(harness, practice, "Old plan", "commercial", active=False)

    refused = await set_usual_payer(harness, practice, retired)
    assert (refused.status_code, refused.json()["message"]) == (422, "choose an active payer")
    assert (await set_usual_payer(harness, practice, medicare)).status_code == 204
    listed = (await harness.client.get("/api/providers", headers=practice.admin)).json()
    assert [row["payer"] for row in listed] == [medicare]

    removed = await harness.client.delete(f"/api/practice/payers/{medicare}", headers=practice.admin)
    assert removed.status_code == 204
    listed = (await harness.client.get("/api/providers", headers=practice.admin)).json()
    assert [row["payer"] for row in listed] == [None]


async def test_turning_a_payer_off_clears_it_as_a_usual_payer(harness):
    practice = await practice_with_provider(harness)
    aetna = await add_payer(harness, practice, "Aetna", "commercial")
    await set_usual_payer(harness, practice, aetna)

    off = {"name": "Aetna", "plan_type": "commercial", "active": False}
    assert (
        await harness.client.put(f"/api/practice/payers/{aetna}", headers=practice.admin, json=off)
    ).status_code == 204

    listed = (await harness.client.get("/api/providers", headers=practice.admin)).json()
    assert [row["payer"] for row in listed] == [None]


def _part(name: str, content: bytes) -> tuple[str, tuple[str, bytes, str]]:
    return ("files", (name, content, "application/pdf"))


async def test_page_one_suggests_the_payer_and_applies_it_only_above_the_threshold(harness):
    practice = await practice_with_provider(harness)
    medicare = await add_payer(harness, practice, "Medicare Part B", "medicare")
    aetna = await add_payer(harness, practice, "Aetna", "commercial")
    parts = [
        _part(
            "face-sheet.pdf", lines_pdf(["Patient: Reyes, Marisol", "Insurance: Medicare Part B", "MBI 1EG4-TE5-MK73"])
        ),
        _part("mention.pdf", lines_pdf(["Follow up visit", "Her Aetna card was scanned at the desk"])),
        _part("blank.pdf", lines_pdf(["Follow up visit", "Stable"])),
    ]

    previewed = await harness.client.post("/api/uploads/preview", headers=practice.admin, files=parts)

    assert previewed.status_code == 200, previewed.text
    rows = previewed.json()
    assert [(row["payer_id"], row["payer_confidence"], row["payer_confident"]) for row in rows] == [
        (medicare, 0.9, True),
        (aetna, 0.6, False),
        (None, 0.0, False),
    ]
    assert "1EG4" not in previewed.text
