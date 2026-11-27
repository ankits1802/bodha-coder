from datetime import timedelta

from sqlalchemy import func, select, update

from app.core.db import SessionFactory
from app.models import PersonTour, Practice, User
from tests.builders import Harness, invite_member, maintenance, practice_with_provider, sign_in

TOURS = "/api/account/tours"
COMPLETED = {"version": 1, "outcome": "completed"}
SKIPPED = {"version": 1, "outcome": "skipped"}
HQ_EMAIL = "hq-admin@lakeside.example.com"


async def put_tour(harness: Harness, headers: dict[str, str], tour: str, body: dict) -> dict:
    response = await harness.client.put(f"{TOURS}/{tour}", headers=headers, json=body)
    assert response.status_code == 200, response.text
    return response.json()


async def test_a_new_person_has_taken_no_tour_and_the_first_outcome_of_a_version_is_kept(harness):
    lakeside = await practice_with_provider(harness)
    assert (await harness.client.get(TOURS, headers=lakeside.admin)).json() == []
    first = await put_tour(harness, lakeside.admin, "practice", COMPLETED)
    assert (first["tour"], first["version"], first["skipped_at"]) == ("practice", 1, None)
    assert first["completed_at"] is not None
    assert await put_tour(harness, lakeside.admin, "practice", SKIPPED) == first
    assert (await harness.client.get(TOURS, headers=lakeside.admin)).json() == [first]


async def test_a_new_version_is_recorded_beside_the_old_one(harness):
    lakeside = await practice_with_provider(harness)
    await put_tour(harness, lakeside.admin, "practice", COMPLETED)
    newer = await put_tour(harness, lakeside.admin, "practice", {"version": 2, "outcome": "skipped"})
    assert (newer["completed_at"], newer["skipped_at"] is not None) == (None, True)
    listed = (await harness.client.get(TOURS, headers=lakeside.admin)).json()
    assert [(row["version"], row["completed_at"] is not None) for row in listed] == [(1, True), (2, False)]


async def test_each_account_reads_and_writes_only_its_own_tour(harness):
    lakeside = await practice_with_provider(harness)
    hq = await sign_in(harness.client, HQ_EMAIL, secret_box=lakeside.secrets)
    await invite_member(harness, lakeside, name="Dev Patel", email="dev@lakeside.example.com", role="coder")
    coder = await sign_in(harness.client, "dev@lakeside.example.com")
    for headers, tour in ((lakeside.admin, "hq"), (coder, "hq"), (hq, "practice")):
        refused = await harness.client.put(f"{TOURS}/{tour}", headers=headers, json=COMPLETED)
        assert (refused.status_code, refused.json()["error"]) == (403, "forbidden")
    hq_record = await put_tour(harness, hq, "hq", SKIPPED)
    admin_record = await put_tour(harness, lakeside.admin, "practice", COMPLETED)
    assert (await harness.client.get(TOURS, headers=hq)).json() == [hq_record]
    assert (await harness.client.get(TOURS, headers=lakeside.admin)).json() == [admin_record]
    assert (await harness.client.get(TOURS, headers=coder)).json() == []


async def test_tours_need_a_session_and_a_known_tour_outcome_and_version(harness):
    lakeside = await practice_with_provider(harness)
    assert (await harness.client.get(TOURS)).status_code == 401
    assert (await harness.client.put(f"{TOURS}/practice", json=COMPLETED)).status_code == 401
    for tour, body in (
        ("elsewhere", COMPLETED),
        ("practice", {"version": 1, "outcome": "dismissed"}),
        ("practice", {"version": 0, "outcome": "completed"}),
        ("practice", {"version": 1001, "outcome": "completed"}),
        ("practice", {"version": 1, "outcome": "completed", "extra": True}),
    ):
        refused = await harness.client.put(f"{TOURS}/{tour}", headers=lakeside.admin, json=body)
        assert refused.status_code == 422, (tour, body)
    assert (await harness.client.get(TOURS, headers=lakeside.admin)).json() == []


async def test_purging_a_practice_removes_its_peoples_tours_and_keeps_hq_tours(harness):
    lakeside = await practice_with_provider(harness)
    hq = await sign_in(harness.client, HQ_EMAIL, secret_box=lakeside.secrets)
    await put_tour(harness, lakeside.admin, "practice", COMPLETED)
    await put_tour(harness, hq, "hq", COMPLETED)
    path = f"/api/hq/practices/{lakeside.id}"
    assert (await harness.client.patch(path, headers=hq, json={"status": "blocked"})).status_code == 204
    closed = await harness.client.post(f"{path}/close", headers=hq, json={"confirm_name": "Lakeside"})
    assert closed.status_code == 204, closed.text
    async with SessionFactory() as db:
        await maintenance(db)
        moment = func.clock_timestamp() - timedelta(days=2558)
        await db.execute(update(Practice).where(Practice.id == lakeside.id).values(closed_at=moment))
        await db.commit()
    purged = await harness.client.post(f"{path}/purge", headers=hq, json={"confirm_name": "Lakeside"})
    assert purged.status_code == 200, purged.text
    async with SessionFactory() as db:
        rows = await db.execute(select(User.email, PersonTour.tour).join(User, User.id == PersonTour.user_id))
    assert rows.all() == [(HQ_EMAIL, "hq")]
