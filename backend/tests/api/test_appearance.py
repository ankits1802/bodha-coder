import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.core.db import SessionFactory
from app.models import User
from tests.builders import Harness, invite_member, practice_with_provider, sign_in

APPEARANCE = "/api/auth/appearance"
HQ_EMAIL = "hq-admin@lakeside.example.com"
ADMIN_EMAIL = "admin@lakeside.example.com"
CODER_EMAIL = "dev@lakeside.example.com"
SYSTEM = {"theme": "system", "text_size": "default", "reduce_motion": "system"}
DARK_AND_LARGER = {"theme": "dark", "text_size": "larger", "reduce_motion": "on"}
LIGHT_AND_LARGE = {"theme": "light", "text_size": "large", "reduce_motion": "off"}


async def put_appearance(harness: Harness, headers: dict[str, str], body: dict[str, str]) -> dict[str, str]:
    response = await harness.client.put(APPEARANCE, headers=headers, json=body)
    assert response.status_code == 200, response.text
    return response.json()


async def test_everyone_starts_on_system_appearance(harness):
    lakeside = await practice_with_provider(harness)
    hq = await sign_in(harness.client, HQ_EMAIL, secret_box=lakeside.secrets)
    for headers in (lakeside.admin, hq):
        response = await harness.client.get(APPEARANCE, headers=headers)
        assert (response.status_code, response.json()) == (200, SYSTEM)


async def test_a_saved_appearance_is_kept_for_that_person_only(harness):
    lakeside = await practice_with_provider(harness)
    await invite_member(harness, lakeside, name="Dev Patel", email=CODER_EMAIL, role="coder")
    coder = await sign_in(harness.client, CODER_EMAIL)
    assert await put_appearance(harness, coder, DARK_AND_LARGER) == DARK_AND_LARGER
    assert (await harness.client.get(APPEARANCE, headers=coder)).json() == DARK_AND_LARGER
    assert (await harness.client.get(APPEARANCE, headers=lakeside.admin)).json() == SYSTEM
    chosen = select(User.theme, User.text_size, User.reduce_motion).where(User.email == CODER_EMAIL)
    async with SessionFactory() as db:
        stored = (await db.execute(chosen)).one()
    assert tuple(stored) == ("dark", "larger", "on")


async def test_a_later_choice_replaces_the_earlier_one_and_follows_a_new_sign_in(harness):
    lakeside = await practice_with_provider(harness)
    hq = await sign_in(harness.client, HQ_EMAIL, secret_box=lakeside.secrets)
    await put_appearance(harness, hq, DARK_AND_LARGER)
    assert await put_appearance(harness, hq, LIGHT_AND_LARGE) == LIGHT_AND_LARGE
    again = await sign_in(harness.client, HQ_EMAIL, secret_box=lakeside.secrets)
    assert (await harness.client.get(APPEARANCE, headers=again)).json() == LIGHT_AND_LARGE


async def test_appearance_needs_a_session_and_known_choices(harness):
    lakeside = await practice_with_provider(harness)
    assert (await harness.client.get(APPEARANCE)).status_code == 401
    assert (await harness.client.put(APPEARANCE, json=SYSTEM)).status_code == 401
    for body in (
        {**SYSTEM, "theme": "sepia"},
        {**SYSTEM, "text_size": "huge"},
        {**SYSTEM, "reduce_motion": "reduce"},
        {"theme": "dark", "text_size": "default"},
        {**SYSTEM, "notify_digest": False},
    ):
        refused = await harness.client.put(APPEARANCE, headers=lakeside.admin, json=body)
        assert refused.status_code == 422, body
    assert (await harness.client.get(APPEARANCE, headers=lakeside.admin)).json() == SYSTEM


@pytest.mark.parametrize("column", ["theme", "text_size", "reduce_motion"])
async def test_the_database_refuses_an_unknown_choice(harness, column):
    await practice_with_provider(harness)
    async with SessionFactory() as db:
        with pytest.raises(IntegrityError):
            await db.execute(update(User).where(User.email == ADMIN_EMAIL).values({column: "blue"}))
