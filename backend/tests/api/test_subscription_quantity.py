from sqlalchemy import func, select

from app.core.db import SessionFactory
from app.models import Activity, Subscription
from app.services.quantity_sync import sync_quantities
from tests.api.billing_helpers import add_provider, configure_prices, provider_body, send_event, stripe_state
from tests.builders import practice_with_provider


async def stored_quantity(practice_id: str) -> int:
    async with SessionFactory() as db:
        return await db.scalar(select(Subscription.quantity).where(Subscription.practice_id == practice_id)) or 0


async def quantity_changes(practice_id: str) -> int:
    async with SessionFactory() as db:
        found = await db.scalar(
            select(func.count())
            .select_from(Activity)
            .where(Activity.practice_id == practice_id, Activity.action == "subscription quantity changed")
        )
        return found or 0


async def test_adding_or_retiring_a_provider_changes_the_billed_quantity(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_with_provider(harness)
    await send_event(harness, "evt_1", stripe_state(practice.id, quantity=1))
    added = await add_provider(harness, practice)
    assert added.status_code == 200
    assert harness.billing["stripe"].quantities == [("sub_1", 2)]
    assert (await stored_quantity(practice.id), await quantity_changes(practice.id)) == (2, 1)
    retired = {**provider_body(active=False), "name": "Elena Varga", "email": "varga@clinic.example.com"}
    edited = await harness.client.put(f"/api/providers/{practice.provider_id}", headers=practice.admin, json=retired)
    assert edited.status_code == 204
    assert harness.billing["stripe"].quantities == [("sub_1", 2), ("sub_1", 1)]
    assert await stored_quantity(practice.id) == 1


async def test_a_failed_quantity_change_never_blocks_the_admin_and_is_retried_by_the_worker(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_with_provider(harness)
    await send_event(harness, "evt_1", stripe_state(practice.id, quantity=1))
    harness.billing["stripe"].unavailable = True
    assert (await add_provider(harness, practice)).status_code == 200
    assert (harness.billing["stripe"].quantities, await stored_quantity(practice.id)) == ([], 1)
    harness.billing["stripe"].unavailable = False
    async with SessionFactory() as db:
        assert await sync_quantities(db, harness.billing) == 1
    assert (harness.billing["stripe"].quantities, await stored_quantity(practice.id)) == ([("sub_1", 2)], 2)
    async with SessionFactory() as db:
        assert await sync_quantities(db, harness.billing) == 0


async def test_a_practice_without_a_live_subscription_is_left_alone(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_with_provider(harness)
    await send_event(harness, "evt_1", stripe_state(practice.id, status="canceled", quantity=1))
    assert (await add_provider(harness, practice)).status_code == 200
    assert harness.billing["stripe"].quantities == []
