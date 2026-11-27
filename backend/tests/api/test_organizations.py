from sqlalchemy import select

from app.core.db import SessionFactory
from app.models import PracticeMembership
from tests.api.membership_helpers import access_log, me, membership_of, signed_in, switch
from tests.api.organization_helpers import (
    GROUP_NAME,
    ORG_ADMIN,
    RIVERBEND_ADMIN,
    organization_of_two,
    organization_path,
    stored_practice,
)
from tests.api.quality_helpers import user_id
from tests.builders import accept_invite

REASON = "Covering month-end coding"
ACCESS = "access granted by organization admin"
PAT = "pat@acme.example.com"


async def test_an_organization_admin_sees_every_practice_and_their_own_role_in_each(harness):
    group = await organization_of_two(harness)

    view = await harness.client.get(organization_path(group), headers=group.lakeside.admin)

    assert view.status_code == 200, view.text
    body = view.json()
    assert (body["name"], body["plan"]) == (GROUP_NAME, "essentials")
    assert {row["name"]: row["my_role"] for row in body["practices"]} == {"Lakeside": "admin", "Riverbend": None}
    assert [admin["email"] for admin in body["admins"]] == [ORG_ADMIN]
    assert (await me(harness, group.lakeside.admin))["organizations"] == [
        {"id": group.id, "name": GROUP_NAME, "role": "admin"}
    ]


async def test_people_who_are_not_organization_admins_cannot_open_it(harness):
    group = await organization_of_two(harness)

    practice_admin = await harness.client.get(organization_path(group), headers=group.riverbend.admin)
    hq = await harness.client.get(organization_path(group), headers=group.hq)

    assert (practice_admin.status_code, hq.status_code) == (404, 404)
    assert (await me(harness, group.riverbend.admin))["organizations"] == []
    assert "organizations" not in (await me(harness, group.hq))


async def test_an_organization_admin_has_no_access_to_a_practice_without_a_membership(harness):
    group = await organization_of_two(harness)
    person = await signed_in(harness, ORG_ADMIN, group.lakeside.secrets)

    refused = await switch(harness, person, group.riverbend.id)

    assert refused.status_code == 403, refused.text
    log = await access_log(harness, group.riverbend.admin)
    assert [entry for entry in log if entry["action"] == "practice switched"] == []
    async with SessionFactory() as db:
        held = await db.scalar(
            select(PracticeMembership.id).where(
                PracticeMembership.user_id == await user_id(ORG_ADMIN),
                PracticeMembership.practice_id == group.riverbend.id,
            )
        )
    assert held is None


async def test_granting_yourself_access_is_recorded_in_the_practice_log_and_told_to_its_admins(harness):
    group = await organization_of_two(harness)
    person = await signed_in(harness, ORG_ADMIN, group.lakeside.secrets)

    granted = await harness.client.post(
        organization_path(group, f"/practices/{group.riverbend.id}/access"),
        headers=person.headers,
        json={"role": "coder", "reason": REASON},
    )

    assert granted.status_code == 204, granted.text
    membership = await membership_of(await user_id(ORG_ADMIN), group.riverbend.id)
    assert (membership.role, membership.status) == ("coder", "active")
    entries = [entry for entry in await access_log(harness, group.riverbend.admin) if entry["action"] == ACCESS]
    assert len(entries) == 1 and REASON in entries[0]["detail"] and GROUP_NAME in entries[0]["detail"]
    told = [body for to, body in harness.messenger.sent if to == RIVERBEND_ADMIN]
    assert told and "gave themselves access to Riverbend" in told[-1] and REASON not in told[-1]
    assert (await switch(harness, person, group.riverbend.id)).status_code == 200
    again = await harness.client.post(
        organization_path(group, f"/practices/{group.riverbend.id}/access"),
        headers=person.headers,
        json={"role": "viewer", "reason": REASON},
    )
    assert again.status_code == 409


async def test_a_person_is_added_to_several_practices_with_a_role_in_each_and_one_invite(harness):
    group = await organization_of_two(harness)
    body = {
        "name": "Pat Lee",
        "email": PAT,
        "practices": [
            {"practice_id": group.lakeside.id, "role": "coder"},
            {"practice_id": group.riverbend.id, "role": "viewer"},
        ],
    }

    added = await harness.client.post(organization_path(group, "/people"), headers=group.lakeside.admin, json=body)

    assert added.status_code == 200, added.text
    person_id = added.json()["id"]
    lakeside = await membership_of(person_id, group.lakeside.id)
    riverbend = await membership_of(person_id, group.riverbend.id)
    assert (lakeside.role, lakeside.status, riverbend.role, riverbend.status) == (
        "coder",
        "invited",
        "viewer",
        "invited",
    )
    assert [to for to, _ in harness.messenger.sent].count(PAT) == 1
    await accept_invite(harness)
    async with SessionFactory() as db:
        statuses = await db.scalars(select(PracticeMembership.status).where(PracticeMembership.user_id == person_id))
        assert set(statuses.all()) == {"active"}
    invited = [
        entry for entry in await access_log(harness, group.riverbend.admin) if entry["action"] == "member invited"
    ]
    assert len(invited) == 1 and GROUP_NAME in invited[0]["detail"]


async def test_adding_a_person_refuses_a_practice_twice_or_one_outside_the_organization(harness):
    group = await organization_of_two(harness)
    twice = [{"practice_id": group.lakeside.id, "role": "coder"}, {"practice_id": group.lakeside.id, "role": "viewer"}]
    outside = [{"practice_id": "no-such-practice", "role": "coder"}]

    doubled = await harness.client.post(
        organization_path(group, "/people"),
        headers=group.lakeside.admin,
        json={"name": "P", "email": PAT, "practices": twice},
    )
    stranger = await harness.client.post(
        organization_path(group, "/people"),
        headers=group.lakeside.admin,
        json={"name": "P", "email": PAT, "practices": outside},
    )
    member = await harness.client.post(
        organization_path(group, "/people"),
        headers=group.lakeside.admin,
        json={
            "name": "R",
            "email": RIVERBEND_ADMIN,
            "practices": [{"practice_id": group.riverbend.id, "role": "coder"}],
        },
    )

    assert (doubled.status_code, stranger.status_code, member.status_code) == (422, 404, 409)


async def test_a_new_practice_joins_the_organization_with_its_plan_and_its_creator_as_admin(harness):
    group = await organization_of_two(harness)

    created = await harness.client.post(
        organization_path(group, "/practices"),
        headers=group.lakeside.admin,
        json={"name": "Hillside", "time_zone": "America/Denver", "agreed": True},
    )

    assert created.status_code == 200, created.text
    practice = await stored_practice(created.json()["id"])
    assert (practice.organization_id, practice.combined_billing, practice.plan, practice.status) == (
        group.id,
        True,
        "essentials",
        "active",
    )
    assert (practice.time_zone, practice.signup["source"]) == ("America/Denver", "organization")
    membership = await membership_of(await user_id(ORG_ADMIN), practice.id)
    assert (membership.role, membership.status) == ("admin", "active")


async def test_combined_insights_list_each_open_practice_and_their_totals(harness):
    group = await organization_of_two(harness)

    found = await harness.client.get(
        organization_path(group, "/insights"), headers=group.lakeside.admin, params={"days": 30}
    )

    assert found.status_code == 200, found.text
    body = found.json()
    assert [row["name"] for row in body["practices"]] == ["Lakeside", "Riverbend"]
    assert body["totals"]["notes"] == sum(row["notes"] for row in body["practices"])
    assert set(body["totals"]["outcomes"]) == {"matched", "billed_too_low", "billed_too_high", "diagnosis_changes"}
