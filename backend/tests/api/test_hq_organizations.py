from datetime import timedelta

from sqlalchemy import func, select, update

from app.core.db import SessionFactory
from app.models import DomainClaim, Organization, OrganizationMembership, Practice, User
from tests.api.billing_helpers import TODAY_UTC
from tests.api.membership_helpers import me
from tests.api.organization_helpers import (
    GROUP_NAME,
    ORG_ADMIN,
    RIVERBEND_ADMIN,
    combine,
    organization_of_two,
    stored_organization,
    stored_practice,
)
from tests.builders import maintenance, practice_with_provider

PURGE_AFTER_DAYS = 2558


async def _backdate_closure(organization_id: str) -> None:
    async with SessionFactory() as db:
        await maintenance(db)
        moment = func.clock_timestamp() - timedelta(days=PURGE_AFTER_DAYS)
        await db.execute(update(Organization).where(Organization.id == organization_id).values(closed_at=moment))
        await db.commit()


async def test_hq_lists_an_organization_with_its_practices_admins_and_plan(harness):
    group = await organization_of_two(harness)
    await combine(harness, group, group.riverbend.id)

    rows = (await harness.client.get("/api/hq/organizations", headers=group.hq)).json()
    page = (await harness.client.get(f"/api/hq/organizations/{group.id}", headers=group.hq)).json()
    practices = {row["id"]: row for row in (await harness.client.get("/api/hq/practices", headers=group.hq)).json()}
    found = (await harness.client.get("/api/hq/search", headers=group.hq, params={"q": "acme"})).json()

    assert [(row["name"], row["practices"], row["combined_practices"], row["admins"]) for row in rows] == [
        (GROUP_NAME, 2, 1, 1)
    ]
    assert rows[0]["providers"] == 1
    assert [row["name"] for row in page["practices"]] == ["Lakeside", "Riverbend"]
    assert [admin["email"] for admin in page["admins"]] == [ORG_ADMIN]
    assert [row["name"] for row in page["plan"]["practices"]] == ["Riverbend"]
    riverbend = practices[group.riverbend.id]
    assert (riverbend["organization_id"], riverbend["organization_name"], riverbend["combined_billing"]) == (
        group.id,
        GROUP_NAME,
        True,
    )
    assert found["organizations"] == [{"id": group.id, "name": GROUP_NAME, "status": "active"}]
    practice_side = await harness.client.get("/api/hq/organizations", headers=group.lakeside.admin)
    assert practice_side.status_code == 403


async def test_a_practice_belongs_to_one_organization_at_a_time(harness):
    group = await organization_of_two(harness)
    other = await harness.client.post("/api/hq/organizations", headers=group.hq, json={"name": "Other Group"})

    moved = await harness.client.post(
        f"/api/hq/organizations/{other.json()['id']}/practices",
        headers=group.hq,
        json={"practice_id": group.lakeside.id},
    )
    detached = await harness.client.delete(
        f"/api/hq/organizations/{group.id}/practices/{group.lakeside.id}", headers=group.hq
    )

    assert (moved.status_code, detached.status_code) == (409, 204)
    assert (await stored_practice(group.lakeside.id)).organization_id is None


async def test_hq_adds_only_existing_practice_accounts_as_organization_admins_and_can_remove_them(harness):
    group = await organization_of_two(harness)
    path = f"/api/hq/organizations/{group.id}/admins"

    unknown = await harness.client.post(
        path, headers=group.hq, json={"email": "nobody@acme.example.com", "reason": "Ops"}
    )
    added = await harness.client.post(
        path, headers=group.hq, json={"email": RIVERBEND_ADMIN, "reason": "Second office"}
    )
    again = await harness.client.post(
        path, headers=group.hq, json={"email": RIVERBEND_ADMIN, "reason": "Second office"}
    )

    assert (unknown.status_code, added.status_code, again.status_code) == (404, 200, 409)
    assert harness.messenger.sent[-1][0] == RIVERBEND_ADMIN
    assert [choice["id"] for choice in (await me(harness, group.riverbend.admin))["organizations"]] == [group.id]
    removed = await harness.client.delete(f"{path}/{added.json()['id']}", headers=group.hq)
    assert removed.status_code == 204
    assert (
        await harness.client.get(f"/api/organizations/{group.id}", headers=group.riverbend.admin)
    ).status_code == 404


async def test_closing_an_organization_detaches_its_practices_and_ends_its_admins(harness):
    group = await organization_of_two(harness)
    await combine(harness, group, group.riverbend.id)
    path = f"/api/hq/organizations/{group.id}"

    misnamed = await harness.client.post(f"{path}/close", headers=group.hq, json={"confirm_name": "acme"})
    closed = await harness.client.post(f"{path}/close", headers=group.hq, json={"confirm_name": GROUP_NAME})

    assert (misnamed.status_code, closed.status_code) == (422, 204)
    organization = await stored_organization(group.id)
    assert organization.status == "closed" and organization.closed_at is not None
    for practice_id in (group.lakeside.id, group.riverbend.id):
        practice = await stored_practice(practice_id)
        assert (practice.organization_id, practice.combined_billing) == (None, False)
    assert (await me(harness, group.lakeside.admin))["organizations"] == []
    assert (await harness.client.patch(path, headers=group.hq, json={"name": "Renamed"})).status_code == 409


async def test_an_organization_is_purged_only_after_the_retention_floor(harness):
    group = await organization_of_two(harness)
    path = f"/api/hq/organizations/{group.id}"
    await harness.client.post(f"{path}/close", headers=group.hq, json={"confirm_name": GROUP_NAME})

    early = await harness.client.post(f"{path}/purge", headers=group.hq, json={"confirm_name": GROUP_NAME})
    await _backdate_closure(group.id)
    purged = await harness.client.post(f"{path}/purge", headers=group.hq, json={"confirm_name": GROUP_NAME})

    assert early.status_code == 409
    assert purged.status_code == 200, purged.text
    assert purged.json()["rows_removed"] >= 1
    assert (await stored_organization(group.id)).status == "purged"
    async with SessionFactory() as db:
        memberships = await db.scalar(
            select(func.count())
            .select_from(OrganizationMembership)
            .where(OrganizationMembership.organization_id == group.id)
        )
        kept = await db.scalar(select(func.count()).select_from(User).where(User.email == ORG_ADMIN))
    assert (memberships, kept) == (0, 1)


async def test_purging_a_practice_keeps_an_organization_admin_who_belonged_only_to_it(harness):
    group = await organization_of_two(harness)
    await harness.client.post(
        f"/api/hq/organizations/{group.id}/admins",
        headers=group.hq,
        json={"email": RIVERBEND_ADMIN, "reason": "Office"},
    )
    claim = await harness.client.post(
        f"/api/organizations/{group.id}/domains",
        headers=group.lakeside.admin,
        json={"domain": "riverbend.example.com", "practice_id": group.riverbend.id},
    )
    assert claim.status_code == 200, claim.text
    practice_path = f"/api/hq/practices/{group.riverbend.id}"
    await harness.client.delete(f"/api/hq/organizations/{group.id}/practices/{group.riverbend.id}", headers=group.hq)
    await harness.client.patch(practice_path, headers=group.hq, json={"status": "ended"})
    assert (
        await harness.client.post(f"{practice_path}/close", headers=group.hq, json={"confirm_name": "Riverbend"})
    ).is_success
    async with SessionFactory() as db:
        await maintenance(db)
        moment = func.clock_timestamp() - timedelta(days=PURGE_AFTER_DAYS)
        await db.execute(update(Practice).where(Practice.id == group.riverbend.id).values(closed_at=moment))
        await db.commit()

    purged = await harness.client.post(f"{practice_path}/purge", headers=group.hq, json={"confirm_name": "Riverbend"})

    assert purged.status_code == 200, purged.text
    async with SessionFactory() as db:
        kept = await db.scalar(select(func.count()).select_from(User).where(User.email == RIVERBEND_ADMIN))
        claims = await db.scalar(
            select(func.count()).select_from(DomainClaim).where(DomainClaim.practice_id == group.riverbend.id)
        )
    assert (kept, claims) == (1, 0)


async def test_spend_can_be_read_for_the_practices_of_one_organization(harness):
    group = await organization_of_two(harness)
    await practice_with_provider(harness, name="Harbor", admin_email="admin@harbor.example.com")
    day = TODAY_UTC.isoformat()

    spend = await harness.client.get(
        "/api/hq/expenditure", headers=group.hq, params={"from": day, "to": day, "organization_id": group.id}
    )
    missing = await harness.client.get(
        "/api/hq/expenditure", headers=group.hq, params={"from": day, "to": day, "organization_id": "nope"}
    )

    assert spend.status_code == 200, spend.text
    assert sorted(row["name"] for row in spend.json()["practices"]) == ["Lakeside", "Riverbend"]
    assert missing.status_code == 404


async def test_the_overview_counts_every_organization_the_list_shows_and_spend_since_the_first_of_the_month(harness):
    group = await organization_of_two(harness)
    bay = await harness.client.post(
        "/api/hq/organizations", headers=group.hq, json={"name": "Bay Group", "plan": "essentials"}
    )
    bay_path = f"/api/hq/organizations/{bay.json()['id']}"
    closed = await harness.client.post(f"{bay_path}/close", headers=group.hq, json={"confirm_name": "Bay Group"})

    listed = (await harness.client.get("/api/hq/organizations", headers=group.hq)).json()
    overview = (await harness.client.get("/api/hq/overview", headers=group.hq)).json()

    assert closed.status_code == 204
    assert [row["name"] for row in listed] == [GROUP_NAME, "Bay Group"]
    assert (overview["organizations"], overview["practices"]) == (2, 2)
    assert overview["month"] == {
        "from": TODAY_UTC.replace(day=1).isoformat(),
        "to": TODAY_UTC.isoformat(),
        "cost_usd": 0.0,
        "unpriced_analyses": 0,
    }
