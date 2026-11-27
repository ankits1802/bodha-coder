from app.services.inbox import Notice
from tests.api.inbox_helpers import entries, inbox_of, write_notice
from tests.api.membership_helpers import SAM, bearer, signed_in, switch, two_practices
from tests.api.quality_helpers import user_id
from tests.api.review_helpers import access_rows
from tests.builders import invite_member, practice_with_provider, sign_in

ADMIN_EMAIL = "admin@lakeside.example.com"
MENTION = Notice("mentioned", "Ana Ruiz", payload={"comment_id": "comment-1", "on": "note"})
EXPIRED = Notice("request_expired", payload={"purpose": "questions"})


def answered(questions: int) -> Notice:
    return Notice("provider_answered", "Elena Varga", payload={"questions": questions})


async def test_a_person_reads_only_their_own_items_in_the_practice_they_are_in(harness):
    pair = await two_practices(harness)
    assert await write_notice(pair.lakeside.id, [pair.sam_id], MENTION) == 1
    assert await write_notice(pair.riverbend.id, [pair.sam_id], EXPIRED) == 1
    sam = await signed_in(harness, SAM)

    in_lakeside = await inbox_of(harness, sam.headers)
    switched = await switch(harness, sam, pair.riverbend.id)
    assert switched.status_code == 200, switched.text
    in_riverbend = await inbox_of(harness, bearer(switched.json()))

    assert entries(in_lakeside) == [("mentioned", "Ana Ruiz", None, {"comment_id": "comment-1", "on": "note"})]
    assert entries(in_riverbend) == [("request_expired", "Bodha", None, {"purpose": "questions"})]
    assert (await inbox_of(harness, pair.lakeside.admin))["items"] == []
    assert (await inbox_of(harness, pair.riverbend.admin))["items"] == []


async def test_unread_items_come_first_and_are_marked_read_one_at_a_time_or_all(harness):
    practice = await practice_with_provider(harness)
    admin_id = await user_id(ADMIN_EMAIL)
    for questions in (1, 2, 3):
        await write_notice(practice.id, [admin_id], answered(questions))
    first = await inbox_of(harness, practice.admin)
    assert ([item["payload"]["questions"] for item in first["items"]], first["unread"], first["total"]) == (
        [3, 2, 1],
        3,
        3,
    )

    newest = first["items"][0]["id"]
    marked = await harness.client.post("/api/inbox/read", headers=practice.admin, json={"ids": [newest]})
    assert marked.json() == {"unread": 2}
    after = await inbox_of(harness, practice.admin)
    assert [item["payload"]["questions"] for item in after["items"]] == [2, 1, 3]
    assert after["items"][2]["read_at"] is not None
    count = await harness.client.get("/api/inbox/count", headers=practice.admin)
    assert count.json() == {"unread": 2}

    everything = await harness.client.post("/api/inbox/read", headers=practice.admin, json={"all": True})
    nothing = await harness.client.post("/api/inbox/read", headers=practice.admin, json={})
    assert (everything.json(), nothing.status_code) == ({"unread": 0}, 422)


async def test_marking_someone_elses_item_read_changes_nothing(harness):
    practice = await practice_with_provider(harness)
    coder_id = await invite_member(
        harness, practice, name="Cora Coder", email="cora@lakeside.example.com", role="coder"
    )
    coder = await sign_in(harness.client, "cora@lakeside.example.com")
    await write_notice(practice.id, [coder_id], answered(1))
    theirs = (await inbox_of(harness, coder))["items"][0]["id"]

    tried = await harness.client.post("/api/inbox/read", headers=practice.admin, json={"ids": [theirs]})

    assert tried.json() == {"unread": 0}
    assert (await inbox_of(harness, coder))["unread"] == 1


async def test_only_active_members_receive_items_and_viewers_have_no_inbox(harness):
    practice = await practice_with_provider(harness)
    blocked_id = await invite_member(
        harness, practice, name="Ben Blocked", email="ben@lakeside.example.com", role="coder"
    )
    blocking = await harness.client.patch(f"/api/team/{blocked_id}", headers=practice.admin, json={"blocked": True})
    assert blocking.status_code in (200, 204), blocking.text
    await invite_member(harness, practice, name="Vic Viewer", email="vic@lakeside.example.com", role="viewer")
    viewer = await sign_in(harness.client, "vic@lakeside.example.com")

    written = await write_notice(practice.id, ["no-such-person", blocked_id], answered(1))

    assert written == 0
    assert (await harness.client.get("/api/inbox", headers=viewer)).status_code == 403
    assert (await harness.client.get("/api/inbox")).status_code == 401


async def test_listing_the_inbox_is_written_to_the_access_log(harness):
    practice = await practice_with_provider(harness)
    await write_notice(practice.id, [await user_id(ADMIN_EMAIL)], answered(2))

    await inbox_of(harness, practice.admin)

    listed = [row for row in await access_rows(harness, practice) if row["action"] == "listed inbox"]
    assert [row["detail"] for row in listed] == ["1 items from 0"]
