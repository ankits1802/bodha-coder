from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.codes.places import UnknownPlaceOfService, setting_for
from app.core.calendar import zone_named
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid, NotFound
from app.models import Activity, Analysis, Note, PlaceOfService, Practice, Provider, User, utcnow
from app.services.audit_log import record_activity
from app.services.auth import end_all_sessions
from app.services.team import send_invite

PLANS = ("trial", "basic", "professional", "enterprise")
STATUSES = ("trial", "active", "ended", "blocked")
ACTIVITY_PAGE = 100


async def overview(db: AsyncSession) -> dict[str, Any]:
    since = utcnow() - timedelta(hours=24)
    by_status = dict((await db.execute(select(Analysis.status, func.count()).group_by(Analysis.status))).all())
    today = (
        await db.execute(
            select(func.count(), func.coalesce(func.sum(Analysis.input_tokens + Analysis.output_tokens), 0)).where(
                Analysis.finished_at >= since, Analysis.status.in_(("succeeded", "superseded"))
            )
        )
    ).one()
    failed = await db.scalar(
        select(func.count()).select_from(Analysis).where(Analysis.finished_at >= since, Analysis.status == "failed")
    )
    return {
        "read_last_24h": today[0],
        "tokens_last_24h": int(today[1]),
        "failed_last_24h": failed or 0,
        "waiting": by_status.get("queued", 0),
        "running": by_status.get("running", 0),
    }


async def practices(db: AsyncSession) -> list[dict[str, Any]]:
    users = dict(
        (
            await db.execute(
                select(User.practice_id, func.count()).where(User.status != "blocked").group_by(User.practice_id)
            )
        ).all()
    )
    providers = dict(
        (await db.execute(select(Provider.practice_id, func.count()).group_by(Provider.practice_id))).all()
    )
    waiting = dict(
        (
            await db.execute(
                select(Note.practice_id, func.count())
                .where(Note.status.in_(("queued", "reading", "ready")))
                .group_by(Note.practice_id)
            )
        ).all()
    )
    rows = await db.scalars(select(Practice).order_by(Practice.name))
    return [
        {
            "id": p.id,
            "name": p.name,
            "status": p.status,
            "plan": p.plan,
            "seats": p.seats,
            "users": users.get(p.id, 0),
            "providers": providers.get(p.id, 0),
            "waiting": waiting.get(p.id, 0),
            "renews_on": p.renews_on.isoformat() if p.renews_on else None,
            "time_zone": p.time_zone,
        }
        for p in rows
    ]


async def create_practice(
    db: AsyncSession,
    messenger: Messenger,
    actor: Actor,
    *,
    name: str,
    admin_name: str,
    admin_email: str,
    plan: str,
    seats: int,
    time_zone: str,
) -> Practice:
    if plan not in PLANS or seats < 1:
        raise Invalid("choose a plan and at least one seat")
    zone_named(time_zone)
    address = admin_email.strip().lower()
    if await db.scalar(select(User.id).where(User.email == address)):
        raise Conflict("someone already uses that email")
    practice = Practice(
        name=name.strip(),
        plan=plan,
        seats=seats,
        status="trial" if plan == "trial" else "active",
        time_zone=time_zone,
    )
    db.add(practice)
    await db.flush()
    admin = User(practice_id=practice.id, email=address, name=admin_name.strip(), role="admin", status="invited")
    db.add(admin)
    await db.flush()
    await send_invite(db, messenger, admin, practice_name=practice.name)
    record_activity(
        db, actor, "practice added", practice_id=practice.id, detail=f"{practice.name}, {plan}, {seats} seats"
    )
    await db.commit()
    return practice


async def update_practice(db: AsyncSession, actor: Actor, practice_id: str, changes: dict[str, Any]) -> Practice:
    practice = await db.get(Practice, practice_id)
    if practice is None:
        raise NotFound("practice not found")
    status, plan, seats = changes.get("status"), changes.get("plan"), changes.get("seats")
    if (status and status not in STATUSES) or (plan and plan not in PLANS) or (seats is not None and seats < 1):
        raise Invalid("status, plan or seats is not allowed")
    if changes.get("time_zone"):
        practice.time_zone = zone_named(changes["time_zone"]).key
    if status and status != practice.status and status in ("ended", "blocked"):
        for user in (await db.scalars(select(User).where(User.practice_id == practice.id))).all():
            await end_all_sessions(db, user)
    practice.status = status or practice.status
    practice.plan = plan or practice.plan
    practice.seats = seats if seats is not None else practice.seats
    if "renews_on" in changes:
        practice.renews_on = changes["renews_on"]
    record_activity(
        db,
        actor,
        "practice updated",
        practice_id=practice.id,
        detail=f"{practice.status}, {practice.plan}, {practice.seats} seats",
    )
    await db.commit()
    return practice


async def places(db: AsyncSession) -> list[PlaceOfService]:
    return list((await db.scalars(select(PlaceOfService).order_by(PlaceOfService.code))).all())


async def set_place(db: AsyncSession, actor: Actor, code: str, *, name: str | None, active: bool) -> PlaceOfService:
    place = await db.get(PlaceOfService, code)
    if place is None:
        if not name:
            raise Invalid("a new place needs a name")
        try:
            setting_for(code)
        except UnknownPlaceOfService as error:
            raise Invalid(f"Bodha has no care setting for place of service {code}") from error
        place = PlaceOfService(code=code, name=name.strip(), active=active)
        db.add(place)
    else:
        place.active, place.name = active, (name or place.name).strip()
    record_activity(
        db,
        actor,
        "place of service changed",
        practice_id=None,
        detail=f"{place.name} ({code}) {'on' if active else 'off'}",
    )
    await db.commit()
    return place


async def activity(db: AsyncSession, *, practice_id: str | None) -> list[Activity]:
    query = select(Activity).order_by(Activity.created_at.desc()).limit(ACTIVITY_PAGE)
    if practice_id:
        query = query.where(Activity.practice_id == practice_id)
    return list((await db.scalars(query)).all())
