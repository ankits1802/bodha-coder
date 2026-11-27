from sqlalchemy import func, select

from app.core.db import SessionFactory
from app.models import Provider
from tests.api.billing_helpers import add_provider, configure_prices, practice_on_plan, send_event, stripe_state
from tests.builders import Practice

CSV_HEADER = "name,credential,email\n"


async def invite(harness, practice: Practice, number: int):
    body = {"name": f"Member {number}", "email": f"member{number}@lakeside.example.com", "role": "coder"}
    return await harness.client.post("/api/team", headers=practice.admin, json=body)


async def provider_count(practice_id: str) -> int:
    async with SessionFactory() as db:
        return (
            await db.scalar(select(func.count()).select_from(Provider).where(Provider.practice_id == practice_id)) or 0
        )


async def test_a_trial_takes_two_active_providers_and_names_the_limit(harness):
    practice = await practice_on_plan(harness, "trial")
    for _ in range(2):
        assert (await add_provider(harness, practice)).status_code == 200
    refused = await add_provider(harness, practice)
    assert (refused.status_code, refused.json()["message"]) == (409, "the Trial plan allows up to 2 active providers")
    assert (await add_provider(harness, practice, active=False)).status_code == 200


async def test_an_import_over_the_limit_adds_nobody(harness):
    practice = await practice_on_plan(harness, "essentials")
    rows = "".join(f"Provider {number},MD,p{number}@clinic.example.com\n" for number in range(4))
    refused = await harness.client.post(
        "/api/providers/import", headers=practice.admin, json={"csv": CSV_HEADER + rows}
    )
    assert (refused.status_code, refused.json()["message"]) == (
        409,
        "the Essentials plan allows up to 3 active providers",
    )
    assert await provider_count(practice.id) == 0


async def test_a_trial_takes_five_users(harness):
    practice = await practice_on_plan(harness, "trial", seats=10)
    for number in range(4):
        assert (await invite(harness, practice, number)).status_code == 200
    refused = await invite(harness, practice, 4)
    assert (refused.status_code, refused.json()["message"]) == (409, "the Trial plan allows up to 5 users")


async def test_seats_set_by_hq_still_cap_a_practice_without_a_subscription(harness):
    practice = await practice_on_plan(harness, "professional", seats=2)
    assert (await invite(harness, practice, 1)).status_code == 200
    refused = await invite(harness, practice, 2)
    assert (refused.status_code, refused.json()["message"]) == (409, "all seats are in use")


async def test_a_paying_practice_follows_its_plan_rather_than_its_seats(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_on_plan(harness, "professional", seats=2)
    await send_event(harness, "evt_1", stripe_state(practice.id, price_id="stripe-professional-monthly"))
    for number in range(3):
        assert (await invite(harness, practice, number)).status_code == 200


async def test_unblocking_a_member_counts_against_the_limit(harness):
    practice = await practice_on_plan(harness, "trial", seats=2)
    first = (await invite(harness, practice, 1)).json()["id"]
    path = f"/api/team/{first}"
    assert (await harness.client.patch(path, headers=practice.admin, json={"blocked": True})).status_code == 204
    assert (await invite(harness, practice, 2)).status_code == 200
    refused = await harness.client.patch(path, headers=practice.admin, json={"blocked": False})
    assert (refused.status_code, refused.json()["message"]) == (409, "all seats are in use")
