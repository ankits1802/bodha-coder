from datetime import date

from sqlalchemy import update

from app.core.db import SessionFactory
from app.models import Organization, Practice
from tests.api.organization_helpers import Group, combine, organization_of_two, organization_path
from tests.builders import PASSWORD, invite_member, sign_in

OFFICE = "dana@lakeside.example.com"
VIEWER = "lee@lakeside.example.com"
ENDED_ON = date(2025, 12, 31)
ENDED = {"error": "plan_ended", "message": "This practice's plan ended on 2025-12-31"}


async def _end_plan(group: Group) -> None:
    async with SessionFactory() as db:
        await db.execute(update(Organization).where(Organization.id == group.id).values(renews_on=ENDED_ON))
        await db.execute(update(Practice).where(Practice.id == group.lakeside.id).values(renews_on=ENDED_ON))
        await db.commit()


async def test_an_organization_admin_without_a_practice_admin_role_keeps_billing_access(harness):
    group = await organization_of_two(harness)
    await combine(harness, group, group.lakeside.id)
    await invite_member(harness, group.lakeside, name="Dana Ruiz", email=OFFICE, role="viewer")
    await invite_member(harness, group.lakeside, name="Lee Chen", email=VIEWER, role="viewer")
    added = await harness.client.post(
        f"/api/hq/organizations/{group.id}/admins", headers=group.hq, json={"email": OFFICE, "reason": "Billing office"}
    )
    assert added.status_code == 200, added.text
    await _end_plan(group)

    office = await sign_in(harness.client, OFFICE, secret_box=group.lakeside.secrets)
    assert (await harness.client.get("/api/auth/me", headers=office)).json()["billing_only"] is True
    plan = await harness.client.get(organization_path(group, "/plan"), headers=office)
    assert plan.status_code == 200, plan.text
    for path in ("/api/today", organization_path(group)):
        refused = await harness.client.get(path, headers=office)
        assert (refused.status_code, refused.json()) == (403, ENDED), path

    viewer = await harness.client.post("/api/auth/login", json={"email": VIEWER, "password": PASSWORD})
    assert (viewer.status_code, viewer.json()) == (403, ENDED)
