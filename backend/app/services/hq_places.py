from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.places import UnknownPlaceOfService, setting_for
from app.core.deps import Actor
from app.core.errors import Invalid
from app.models import DemoRequest, PlaceOfService
from app.services.audit_log import record_activity

__all__ = ["demo_requests", "places", "set_place"]


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


async def demo_requests(db: AsyncSession) -> list[DemoRequest]:
    return list((await db.scalars(select(DemoRequest).order_by(DemoRequest.created_at.desc()).limit(200))).all())
