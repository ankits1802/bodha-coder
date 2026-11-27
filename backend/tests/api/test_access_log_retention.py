from datetime import timedelta

import pytest
from sqlalchemy import DateTime, String, bindparam, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.db import SessionFactory
from app.models import AccessLog, AuditChainAnchor, Practice, utcnow
from app.services.retention import purge_access_logs
from tests.builders import maintenance, practice_with_provider

VERIFY = text("SELECT problem FROM bodha_verify_chain(:chain)").bindparams(bindparam("chain", type_=String))
PURGE = text("SELECT bodha_purge_access_log(:practice, :cutoff)").bindparams(
    bindparam("practice", type_=String), bindparam("cutoff", type_=DateTime(timezone=True))
)
OLDEST, OLDER, OLD, RECENT = 3700, 3000, 2600, 2500


async def _quiet_practice(name: str, years: int) -> str:
    async with SessionFactory() as db:
        practice = Practice(name=name, status="active", plan="professional", access_log_years=years)
        db.add(practice)
        await db.commit()
        return practice.id


async def _entries(practice_id: str, *ages_in_days: int) -> None:
    async with SessionFactory() as db:
        await maintenance(db)
        for age in sorted(ages_in_days, reverse=True):
            db.add(_entry(practice_id, f"{age} days ago", created_at=utcnow() - timedelta(days=age)))
            await db.flush()
        await db.commit()
    async with SessionFactory() as db:
        db.add(_entry(practice_id, "today"))
        await db.commit()


def _entry(practice_id: str, action: str, **values) -> AccessLog:
    return AccessLog(
        practice_id=practice_id, actor_kind="user", actor_id="u-old", actor_name="Coder", action=action, **values
    )


async def _kept(practice_id: str) -> list[str]:
    async with SessionFactory() as db:
        query = select(AccessLog.action).where(AccessLog.practice_id == practice_id).order_by(AccessLog.chain_seq)
        return list((await db.scalars(query)).all())


async def test_each_practice_keeps_its_access_log_for_its_years_and_never_under_2557_days(harness):
    seven, ten = await _quiet_practice("Lakeside", 7), await _quiet_practice("Harbor", 10)
    for practice_id in (seven, ten):
        await _entries(practice_id, OLDEST, OLDER, OLD, RECENT)

    async with SessionFactory() as db:
        assert await purge_access_logs(db, utcnow()) == 4

    assert await _kept(seven) == [f"{RECENT} days ago", "today"]
    assert await _kept(ten) == [f"{OLDER} days ago", f"{OLD} days ago", f"{RECENT} days ago", "today"]
    async with SessionFactory() as db:
        anchors = (await db.execute(select(AuditChainAnchor.chain, AuditChainAnchor.rows_removed))).all()
        problems = [await db.scalar(VERIFY, {"chain": f"access_log:{practice}"}) for practice in (seven, ten)]
    assert sorted(anchors) == sorted([(f"access_log:{seven}", 3), (f"access_log:{ten}", 1)])
    assert problems == [None, None]


async def test_the_database_refuses_to_purge_entries_younger_than_2557_days(harness):
    practice_id = await _quiet_practice("Lakeside", 7)
    await _entries(practice_id, RECENT)
    async with SessionFactory() as db:
        with pytest.raises(DBAPIError, match="younger than 2557 days"):
            await db.scalar(PURGE, {"practice": practice_id, "cutoff": utcnow() - timedelta(days=2556)})


async def test_no_practice_keeps_its_access_log_for_less_than_seven_years(harness):
    async with SessionFactory() as db:
        db.add(Practice(name="Lakeside", status="active", plan="professional", access_log_years=6))
        with pytest.raises(IntegrityError):
            await db.commit()


async def _keep_for(harness, practice, years: int) -> int:
    setup = (await harness.client.get("/api/practice/setup", headers=practice.admin)).json()["security"]
    body = {"mfa_roles": setup["mfa_roles"], "idle_minutes": setup["idle_minutes"], "access_log_years": years}
    return (await harness.client.put("/api/practice/security", headers=practice.admin, json=body)).status_code


async def test_the_access_log_is_kept_seven_to_ten_years(harness):
    practice = await practice_with_provider(harness)
    assert (await harness.client.get("/api/practice/setup", headers=practice.admin)).json()["security"][
        "access_log_years"
    ] == 7
    assert await _keep_for(harness, practice, 6) == 422
    assert await _keep_for(harness, practice, 11) == 422
    assert await _keep_for(harness, practice, 8) == 204
    security = (await harness.client.get("/api/practice/setup", headers=practice.admin)).json()["security"]
    assert security["access_log_years"] == 8
