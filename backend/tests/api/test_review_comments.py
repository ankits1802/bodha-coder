import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.db import SessionFactory
from tests.api.review_helpers import access_rows
from tests.builders import invite_member, practice_with_provider, reviewed_note, sign_in

BODY = "Reyes chart: level looks right to me"


async def _team(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    coder_id = await invite_member(
        harness, practice, name="Cora Coder", email="cora@lakeside.example.com", role="coder"
    )
    viewer_id = await invite_member(
        harness, practice, name="Vic Viewer", email="vic@lakeside.example.com", role="viewer"
    )
    coder = await sign_in(harness.client, "cora@lakeside.example.com")
    return practice, note_id, coder, coder_id, viewer_id


async def _post(harness, headers, note_id: str, body: dict):
    return await harness.client.post(f"/api/notes/{note_id}/comments", headers=headers, json=body)


async def _listed(harness, headers, note_id: str, *, removed: bool = False):
    return await harness.client.get(f"/api/notes/{note_id}/comments", headers=headers, params={"removed": removed})


async def test_a_mention_emails_a_link_and_the_practice_name_only(harness, icd_catalog):
    practice, note_id, _, coder_id, _ = await _team(harness, icd_catalog)
    sent_before = len(harness.messenger.sent)

    posted = await _post(harness, practice.admin, note_id, {"finding_key": "em", "body": BODY, "mentions": [coder_id]})

    assert posted.status_code == 200, posted.text
    comment = posted.json()
    assert (comment["finding_key"], comment["author_role"], comment["mentions"]) == (
        "em",
        "admin",
        [{"id": coder_id, "name": "Cora Coder"}],
    )
    [(to, message)] = harness.messenger.sent[sent_before:]
    assert to == "cora@lakeside.example.com"
    assert message.startswith("Lakeside: you were mentioned") and f"/notes/{note_id}?tab=history" in message
    assert "Reyes" not in message and "level" not in message


@pytest.mark.parametrize("body", [{"body": "x", "finding_key": "dx:Z99.9"}, {"body": "x", "mentions": ["nobody"]}])
async def test_comments_name_real_findings_and_mention_only_note_readers(harness, icd_catalog, body):
    practice, note_id, _, _, viewer_id = await _team(harness, icd_catalog)

    refused = await _post(harness, practice.admin, note_id, body)
    viewer = await _post(harness, practice.admin, note_id, {"body": "x", "mentions": [viewer_id]})

    assert (refused.status_code, viewer.status_code) == (422, 422)


async def test_removing_hides_a_comment_but_keeps_it_with_who_removed_it(harness, icd_catalog):
    practice, note_id, coder, _, _ = await _team(harness, icd_catalog)
    mine = (await _post(harness, coder, note_id, {"body": "first thought"})).json()
    theirs = (await _post(harness, practice.admin, note_id, {"body": "admin note"})).json()
    assert (mine["can_remove"], theirs["can_remove"]) == (True, True)

    forbidden = await harness.client.post(f"/api/comments/{theirs['id']}/remove", headers=coder)
    removed = await harness.client.post(f"/api/comments/{mine['id']}/remove", headers=coder)
    twice = await harness.client.post(f"/api/comments/{mine['id']}/remove", headers=practice.admin)

    assert (forbidden.status_code, removed.status_code, twice.status_code) == (403, 200, 409)
    assert [item["id"] for item in (await _listed(harness, coder, note_id)).json()["items"]] == [theirs["id"]]
    assert (await _listed(harness, coder, note_id, removed=True)).status_code == 403
    every = (await _listed(harness, practice.admin, note_id, removed=True)).json()["items"]
    assert [(item["body"], item["removed"] and item["removed"]["by"]) for item in every] == [
        ("first thought", "Cora Coder"),
        ("admin note", None),
    ]
    actions = [row["action"] for row in await access_rows(harness, practice)]
    assert actions.count("commented") == 2 and actions.count("removed comment") == 1


async def test_comments_are_never_edited_in_place(harness, icd_catalog):
    practice, note_id, _, _, _ = await _team(harness, icd_catalog)
    await _post(harness, practice.admin, note_id, {"body": "kept as written"})

    async with SessionFactory() as db:
        with pytest.raises(DBAPIError, match="append-only"):
            await db.execute(text("UPDATE review_comments SET body = 'rewritten'"))


async def test_another_practice_cannot_read_or_comment(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    other = await practice_with_provider(harness, name="Hillcrest", admin_email="admin@hillcrest.example.com")
    await _post(harness, practice.admin, note_id, {"body": "inside"})

    assert (await _listed(harness, other.admin, note_id)).status_code == 404
    assert (await _post(harness, other.admin, note_id, {"body": "outside"})).status_code == 404
    people = (await harness.client.get("/api/comments/people", headers=other.admin)).json()
    assert [person["name"] for person in people] == ["Practice Admin"]
