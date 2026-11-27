from sqlalchemy import select, update

from app.core.db import SessionFactory
from app.models import User
from tests.api.membership_helpers import SAM, membership_of, two_practices
from tests.builders import practice_with_provider

OLD = "old@lakeside.example.com"


async def legacy_link(email: str) -> str | None:
    async with SessionFactory() as db:
        return await db.scalar(select(User.legacy_practice_id).where(User.email == email))


async def test_a_practice_user_written_by_the_release_before_gets_a_matching_membership(harness):
    practice = await practice_with_provider(harness)
    async with SessionFactory() as db:
        person = User(email=OLD, name="Old Way", role="biller", status="invited", legacy_practice_id=practice.id)
        db.add(person)
        await db.commit()
        person_id = person.id
        await db.execute(update(User).where(User.id == person_id).values(role="compliance", status="active"))
        await db.commit()
    membership = await membership_of(person_id, practice.id)
    assert (membership.role, membership.status, membership.ended_at) == ("compliance", "active", None)


async def test_new_accounts_and_changed_memberships_leave_the_old_column_empty(harness):
    both = await two_practices(harness)
    assert await legacy_link(SAM) is None
    assert await legacy_link("admin@riverbend.example.com") is None
    async with SessionFactory() as db:
        await db.execute(update(User).where(User.id == both.sam_id).values(legacy_practice_id=both.lakeside.id))
        await db.commit()
    blocked = await harness.client.patch(
        f"/api/team/{both.sam_id}", headers=both.lakeside.admin, json={"blocked": True}
    )
    assert blocked.status_code == 204
    assert await legacy_link(SAM) is None
    async with SessionFactory() as db:
        await db.execute(update(User).where(User.id == both.sam_id).values(status="active"))
        await db.commit()
    assert (await membership_of(both.sam_id, both.lakeside.id)).status == "blocked"
