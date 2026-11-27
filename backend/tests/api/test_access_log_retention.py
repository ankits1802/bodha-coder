from datetime import UTC, datetime

from sqlalchemy import select

from app.core.db import SessionFactory
from app.models import AccessLog
from app.services.records import purge_access_logs
from tests.builders import practice_with_provider

NOON = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)
LATE_EVENING_IN_CHICAGO = datetime(2026, 11, 27, 3, 0, tzinfo=UTC)
SIX_YEARS_BEFORE_MIDNIGHT = datetime(2020, 11, 27, 5, 59, 59, tzinfo=UTC)
SIX_YEARS_AT_MIDNIGHT = datetime(2020, 11, 27, 6, 0, tzinfo=UTC)
TEN_YEARS_BEFORE_MIDNIGHT = datetime(2016, 11, 27, 5, 59, 59, tzinfo=UTC)
TEN_YEARS_AT_MIDNIGHT = datetime(2016, 11, 27, 6, 0, tzinfo=UTC)


async def _old_entries(practice_id: str, *moments: datetime) -> None:
    async with SessionFactory() as db:
        for moment in moments:
            db.add(
                AccessLog(
                    practice_id=practice_id,
                    actor_kind="user",
                    actor_id="u-old",
                    actor_name="Former coder",
                    action=f"opened note at {moment.isoformat()}",
                    created_at=moment,
                )
            )
        await db.commit()


async def _kept(practice_id: str) -> list[str]:
    async with SessionFactory() as db:
        rows = await db.scalars(
            select(AccessLog.action).where(AccessLog.practice_id == practice_id, AccessLog.actor_id == "u-old")
        )
        return sorted(rows.all())


async def _keep_for(harness, practice, years: int) -> int:
    setup = (await harness.client.get("/api/practice/setup", headers=practice.admin)).json()["security"]
    body = {"mfa_roles": setup["mfa_roles"], "idle_minutes": setup["idle_minutes"], "access_log_years": years}
    return (await harness.client.put("/api/practice/security", headers=practice.admin, json=body)).status_code


async def test_each_practice_keeps_its_access_log_for_its_own_number_of_years(harness):
    lakeside = await practice_with_provider(harness)
    harbor = await practice_with_provider(harness, name="Harbor", admin_email="admin@harbor.example.com")
    assert await _keep_for(harness, harbor, 10) == 204
    old = (TEN_YEARS_BEFORE_MIDNIGHT, TEN_YEARS_AT_MIDNIGHT, SIX_YEARS_BEFORE_MIDNIGHT, SIX_YEARS_AT_MIDNIGHT)
    await _old_entries(lakeside.id, *old)
    await _old_entries(harbor.id, *old)

    async with SessionFactory() as db:
        assert await purge_access_logs(db, NOON) == 4

    assert await _kept(lakeside.id) == [f"opened note at {SIX_YEARS_AT_MIDNIGHT.isoformat()}"]
    assert await _kept(harbor.id) == sorted(
        f"opened note at {moment.isoformat()}"
        for moment in (TEN_YEARS_AT_MIDNIGHT, SIX_YEARS_BEFORE_MIDNIGHT, SIX_YEARS_AT_MIDNIGHT)
    )
    recent = (await harness.client.get("/api/access-log", headers=lakeside.admin)).json()
    assert recent["total"] >= 1


async def test_the_cutoff_follows_the_practice_calendar_day(harness):
    practice = await practice_with_provider(harness)
    await _old_entries(practice.id, SIX_YEARS_BEFORE_MIDNIGHT)
    async with SessionFactory() as db:
        assert await purge_access_logs(db, LATE_EVENING_IN_CHICAGO) == 0
    assert len(await _kept(practice.id)) == 1
    async with SessionFactory() as db:
        assert await purge_access_logs(db, NOON) == 1
    assert await _kept(practice.id) == []


async def test_the_access_log_is_kept_six_to_ten_years(harness):
    practice = await practice_with_provider(harness)
    assert (await harness.client.get("/api/practice/setup", headers=practice.admin)).json()["security"][
        "access_log_years"
    ] == 6
    assert await _keep_for(harness, practice, 5) == 422
    assert await _keep_for(harness, practice, 11) == 422
    assert await _keep_for(harness, practice, 8) == 204
    security = (await harness.client.get("/api/practice/setup", headers=practice.admin)).json()["security"]
    assert security["access_log_years"] == 8
