from sqlalchemy import func, select

from app.core.db import SessionFactory
from app.models import Practice
from tests.api.billing_helpers import practice_on_plan
from tests.api.inbox_helpers import entries, inbox_of
from tests.api.membership_helpers import access_log, membership_of
from tests.api.organization_helpers import join_rows, join_token, verified_domain
from tests.api.quality_helpers import user_id
from tests.builders import accept_invite, back_from_google, practice_with_provider

DANA = "dana@lakeside.example.com"
SIGNUP = {
    "name": "Dana Fox",
    "practice_name": "Dana Pediatrics",
    "email": DANA,
    "time_zone": "America/Chicago",
    "agreed": True,
}


async def _signed_up(harness) -> str:
    response = await harness.client.post("/api/signup", json=SIGNUP)
    assert response.status_code == 204, response.text
    return join_token(harness, DANA)


async def _practices_named(name: str) -> int:
    async with SessionFactory() as db:
        return await db.scalar(select(func.count()).select_from(Practice).where(Practice.name == name)) or 0


async def test_signing_up_with_a_claimed_domain_offers_the_practice_instead_of_creating_one(harness):
    practice = await practice_with_provider(harness)
    await verified_domain(harness, practice.admin, mode="request")

    token = await _signed_up(harness)
    offer = await harness.client.post("/api/signup/join/offer", json={"token": token})

    assert await _practices_named("Dana Pediatrics") == 0
    assert offer.json() == {
        "email": DANA,
        "name": "Dana Fox",
        "own_practice_name": "Dana Pediatrics",
        "join": {"practice_name": "Lakeside", "mode": "request"},
    }


async def test_a_request_to_join_reaches_the_admins_and_an_approval_sends_the_invite(harness):
    practice = await practice_with_provider(harness)
    await verified_domain(harness, practice.admin, mode="request", role="viewer")
    token = await _signed_up(harness)

    requested = await harness.client.post("/api/signup/join", json={"token": token, "join": True})

    assert requested.json() == {"outcome": "requested"}
    waiting = (await harness.client.get("/api/team/join-requests", headers=practice.admin)).json()
    assert [(row["name"], row["email"], row["suggested_role"]) for row in waiting] == [("Dana Fox", DANA, "viewer")]
    request_id = waiting[0]["id"]
    assert entries(await inbox_of(harness, practice.admin)) == [
        ("join_requested", "Dana Fox", None, {"request_id": request_id})
    ]
    approved = await harness.client.post(
        f"/api/team/join-requests/{request_id}/approve", headers=practice.admin, json={"role": "coder"}
    )
    assert approved.status_code == 200, approved.text
    assert harness.messenger.sent[-1][0] == DANA
    await accept_invite(harness)
    membership = await membership_of(approved.json()["id"], practice.id)
    assert (membership.role, membership.status) == ("coder", "active")
    assert (await inbox_of(harness, practice.admin))["unread"] == 0
    assert [row.status for row in await join_rows(practice.id)] == ["approved"]
    actions = [entry["action"] for entry in await access_log(harness, practice.admin)]
    assert "join requested" in actions and "join request approved" in actions


async def test_a_declined_request_leaves_the_list_and_creates_no_account(harness):
    practice = await practice_with_provider(harness)
    await verified_domain(harness, practice.admin, mode="request")
    token = await _signed_up(harness)
    await harness.client.post("/api/signup/join", json={"token": token, "join": True})
    request_id = (await harness.client.get("/api/team/join-requests", headers=practice.admin)).json()[0]["id"]

    declined = await harness.client.post(f"/api/team/join-requests/{request_id}/decline", headers=practice.admin)

    assert declined.status_code == 204
    assert (await harness.client.get("/api/team/join-requests", headers=practice.admin)).json() == []
    assert await user_id(DANA) is None
    again = await harness.client.post(f"/api/team/join-requests/{request_id}/decline", headers=practice.admin)
    assert again.status_code == 404


async def test_joining_automatically_gives_the_chosen_role_once_the_password_is_set(harness):
    practice = await practice_with_provider(harness)
    await verified_domain(harness, practice.admin, mode="auto", role="viewer")
    token = await _signed_up(harness)

    joined = await harness.client.post("/api/signup/join", json={"token": token, "join": True})

    assert joined.json() == {"outcome": "joined"}
    person = await user_id(DANA)
    assert (await membership_of(person, practice.id)).status == "invited"
    await accept_invite(harness)
    membership = await membership_of(person, practice.id)
    assert (membership.role, membership.status) == ("viewer", "active")
    rows = await join_rows(practice.id)
    assert [(row.status, row.role, row.user_id) for row in rows] == [("joined", "viewer", person)]
    joins = [
        entry for entry in await access_log(harness, practice.admin) if entry["action"] == "joined by email domain"
    ]
    assert len(joins) == 1 and joins[0]["actor_kind"] == "system"
    twice = await harness.client.post("/api/signup/join", json={"token": token, "join": True})
    assert twice.status_code == 409


async def test_a_full_practice_takes_a_request_instead_of_an_automatic_join(harness):
    practice = await practice_on_plan(harness, "professional", seats=1)
    await verified_domain(harness, practice.admin, mode="auto")
    token = await _signed_up(harness)

    joined = await harness.client.post("/api/signup/join", json={"token": token, "join": True})

    assert joined.json() == {"outcome": "requested"}
    assert [row.status for row in await join_rows(practice.id)] == ["pending"]


async def test_the_person_can_start_their_own_practice_from_the_offer(harness):
    practice = await practice_with_provider(harness)
    await verified_domain(harness, practice.admin, mode="auto")
    token = await _signed_up(harness)

    started = await harness.client.post("/api/signup/join", json={"token": token, "join": False})

    assert started.json() == {"outcome": "started"}
    assert await _practices_named("Dana Pediatrics") == 1
    assert await join_rows(practice.id) == []


async def test_a_sign_in_service_sign_up_joins_automatically_and_enters_the_practice(harness):
    practice = await practice_with_provider(harness)
    await verified_domain(harness, practice.admin, mode="auto", role="viewer")
    harness.google.returns("code-dana", subject="google-dana", email=DANA, name="Dana Fox")
    await back_from_google(harness, "code-dana")

    pending = await harness.client.get("/api/signup/identity")
    joined = await harness.client.post("/api/signup/identity/join", json={"name": "Dana Fox"})

    assert pending.json()["join"] == {"practice_name": "Lakeside", "mode": "auto"}
    assert joined.status_code == 200, joined.text
    user = joined.json()["user"]
    assert (user["practice"]["id"], user["role"]) == (practice.id, "viewer")


async def test_a_sign_in_service_sign_up_can_ask_to_join(harness):
    practice = await practice_with_provider(harness)
    await verified_domain(harness, practice.admin, mode="request")
    harness.google.returns("code-dana", subject="google-dana", email=DANA, name="Dana Fox")
    await back_from_google(harness, "code-dana")

    asked = await harness.client.post("/api/signup/identity/join", json={"name": "Dana Fox"})

    assert asked.json() == {"outcome": "requested"}
    assert await user_id(DANA) is None
    assert [row.email for row in await join_rows(practice.id)] == [DANA]


async def test_a_released_domain_no_longer_offers_the_practice(harness):
    practice = await practice_with_provider(harness)
    claim_id = await verified_domain(harness, practice.admin, mode="auto")
    await harness.client.delete(f"/api/practice/domains/{claim_id}", headers=practice.admin)

    response = await harness.client.post("/api/signup", json=SIGNUP)

    assert response.status_code == 204
    assert await _practices_named("Dana Pediatrics") == 1
