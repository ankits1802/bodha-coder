from datetime import date, timedelta

from sqlalchemy import select, update

from app.core.db import SessionFactory
from app.models import Organization, Subscription
from tests.api.billing_helpers import (
    LAST_PAID_DAY,
    TODAY_UTC,
    add_provider,
    configure_prices,
    send_event,
    stripe_state,
)
from tests.api.membership_helpers import me
from tests.api.organization_helpers import (
    GROUP_NAME,
    combine,
    organization_of_two,
    organization_path,
    stored_organization,
    stored_practice,
)

CHECKOUT = {"plan": "essentials", "interval": "monthly", "provider": "stripe"}
ENDED_ON = date(2025, 12, 31)


def organization_state(organization_id: str, **changes):
    return stripe_state(None, organization_id=organization_id, subscription_id="sub_org", **changes)


async def organization_subscription(organization_id: str) -> Subscription | None:
    async with SessionFactory() as db:
        return await db.scalar(select(Subscription).where(Subscription.organization_id == organization_id))


async def test_a_practice_in_combined_billing_takes_the_organization_plan_and_keeps_it_when_it_leaves(harness):
    group = await organization_of_two(harness, plan="trial")
    organization = await stored_organization(group.id)

    await combine(harness, group, group.riverbend.id)

    joined = await stored_practice(group.riverbend.id)
    assert (joined.combined_billing, joined.plan, joined.status, joined.renews_on) == (
        True,
        "trial",
        "trial",
        organization.renews_on,
    )
    await combine(harness, group, group.riverbend.id, combined=False)
    left = await stored_practice(group.riverbend.id)
    assert (left.combined_billing, left.plan, left.renews_on) == (False, "trial", organization.renews_on)


async def test_a_practice_with_its_own_live_subscription_cannot_join_combined_billing(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    group = await organization_of_two(harness)
    assert (await send_event(harness, "evt_own", stripe_state(group.riverbend.id))).status_code == 204

    refused = await harness.client.put(
        organization_path(group, f"/practices/{group.riverbend.id}/billing"),
        headers=group.lakeside.admin,
        json={"combined": True},
    )

    assert refused.status_code == 409, refused.text
    assert (await stored_practice(group.riverbend.id)).combined_billing is False


async def test_combined_checkout_bills_every_active_provider_across_the_combined_practices(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    group = await organization_of_two(harness)
    nothing = await harness.client.post(
        organization_path(group, "/plan/checkout"), headers=group.lakeside.admin, json=CHECKOUT
    )
    await combine(harness, group, group.lakeside.id)
    await combine(harness, group, group.riverbend.id)
    assert (await add_provider(harness, group.riverbend)).status_code == 200

    started = await harness.client.post(
        organization_path(group, "/plan/checkout"), headers=group.lakeside.admin, json=CHECKOUT
    )

    assert nothing.status_code == 409
    assert started.status_code == 200, started.text
    request = harness.billing["stripe"].checkouts[-1]
    assert (request.organization_id, request.practice_id, request.quantity) == (group.id, None, 3)
    assert request.success_url.endswith(f"/organizations/{group.id}/plan?checkout=done")


async def test_a_webhook_for_the_organization_opens_every_combined_practice_until_the_period_end(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    group = await organization_of_two(harness, plan="trial")
    await combine(harness, group, group.lakeside.id)
    await combine(harness, group, group.riverbend.id)

    delivered = await send_event(harness, "evt_org", organization_state(group.id, quantity=2))

    assert delivered.status_code == 204, delivered.text
    stored = await organization_subscription(group.id)
    assert stored is not None and (stored.practice_id, stored.status, stored.quantity) == (None, "active", 2)
    organization = await stored_organization(group.id)
    assert (organization.plan, organization.renews_on) == ("essentials", LAST_PAID_DAY)
    for practice_id in (group.lakeside.id, group.riverbend.id):
        practice = await stored_practice(practice_id)
        assert (practice.status, practice.plan, practice.renews_on) == ("active", "essentials", LAST_PAID_DAY)
    view = (await harness.client.get("/api/plan", headers=group.riverbend.admin)).json()
    assert (view["standing"], view["organization"]) == ("active", {"id": group.id, "name": GROUP_NAME})
    own = await harness.client.post("/api/plan/checkout", headers=group.riverbend.admin, json=CHECKOUT)
    assert own.status_code == 409
    plan = (await harness.client.get(organization_path(group, "/plan"), headers=group.lakeside.admin)).json()
    assert (plan["standing"], plan["providers"], plan["subscription"]["quantity"]) == ("active", 2, 2)


async def test_the_organization_plan_limits_providers_in_each_practice(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    group = await organization_of_two(harness)
    await combine(harness, group, group.lakeside.id)
    await send_event(harness, "evt_org", organization_state(group.id, quantity=1))
    for _ in range(2):
        assert (await add_provider(harness, group.lakeside)).status_code == 200

    refused = await add_provider(harness, group.lakeside)

    assert refused.status_code == 409
    assert refused.json()["message"] == "the Essentials plan allows up to 3 active providers"
    assert ("sub_org", 3) in harness.billing["stripe"].quantities


async def test_a_combined_practice_follows_the_organization_into_billing_only(harness):
    group = await organization_of_two(harness)
    await combine(harness, group, group.riverbend.id)
    async with SessionFactory() as db:
        await db.execute(update(Organization).where(Organization.id == group.id).values(renews_on=ENDED_ON))
        await db.commit()

    renamed = await harness.client.patch(
        f"/api/hq/organizations/{group.id}", headers=group.hq, json={"name": "Acme Health Group"}
    )

    assert renamed.status_code == 204, renamed.text
    assert (await stored_practice(group.riverbend.id)).renews_on == ENDED_ON
    assert (await me(harness, group.riverbend.admin))["billing_only"] is True
    assert (await stored_practice(group.lakeside.id)).renews_on != ENDED_ON


async def test_hq_renews_an_organization_by_hand_and_its_combined_practices_follow(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    group = await organization_of_two(harness)
    await combine(harness, group, group.riverbend.id)
    until = TODAY_UTC + timedelta(days=90)

    renewed = await harness.client.post(
        f"/api/hq/organizations/{group.id}/renew", headers=group.hq, json={"until": until.isoformat()}
    )
    practice_change = await harness.client.patch(
        f"/api/hq/practices/{group.riverbend.id}", headers=group.hq, json={"plan": "professional"}
    )
    ended = await harness.client.patch(
        f"/api/hq/practices/{group.riverbend.id}", headers=group.hq, json={"status": "ended"}
    )
    closing = await harness.client.post(
        f"/api/hq/practices/{group.riverbend.id}/close", headers=group.hq, json={"confirm_name": "Riverbend"}
    )

    assert (renewed.status_code, renewed.json()["renews_on"]) == (200, until.isoformat())
    assert (await stored_practice(group.riverbend.id)).renews_on == until
    assert (practice_change.status_code, ended.status_code) == (409, 204)
    assert (closing.status_code, closing.json()["message"]) == (
        409,
        "take the practice out of combined billing before closing it",
    )
    await send_event(harness, "evt_org", organization_state(group.id))
    assert (await stored_practice(group.riverbend.id)).status == "ended"
    paid = await harness.client.post(
        f"/api/hq/organizations/{group.id}/renew", headers=group.hq, json={"until": until.isoformat()}
    )
    assert paid.status_code == 409
