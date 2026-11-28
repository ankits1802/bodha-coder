from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.bodies import ImportBody
from app.api.clearinghouse_bodies import ChargeBody, ConnectionBody, HostKeyBody
from app.api.responses.base import ExactRoute
from app.api.responses.clearinghouse import ChargeList, ClearinghouseView, ConnectionCheck, HostKey
from app.api.wiring import Link
from app.core.deps import Actor, Db, require
from app.core.roles import ADMINS
from app.services import charge_schedule, clearinghouse_settings
from app.services.clearinghouse_settings import ConnectionValues

router = APIRouter(tags=["clearinghouse"], route_class=ExactRoute)
Admin = Annotated[Actor, Depends(require(*ADMINS))]
CLEARINGHOUSE = "/practice/clearinghouse"
CHARGES = "/practice/charges"


@router.get(CLEARINGHOUSE, response_model=ClearinghouseView)
async def clearinghouse(db: Db, actor: Admin) -> dict[str, Any]:
    return await clearinghouse_settings.clearinghouse_view(db, actor)


@router.put(CLEARINGHOUSE, response_model=ClearinghouseView)
async def save_clearinghouse(body: ConnectionBody, db: Db, actor: Admin) -> dict[str, Any]:
    return await clearinghouse_settings.save_connection(db, actor, ConnectionValues(**body.model_dump()))


@router.delete(CLEARINGHOUSE, response_model=ClearinghouseView)
async def remove_clearinghouse(db: Db, actor: Admin) -> dict[str, Any]:
    return await clearinghouse_settings.remove_connection(db, actor)


@router.post(f"{CLEARINGHOUSE}/host-key", response_model=HostKey)
async def host_key(body: HostKeyBody, db: Db, link: Link, actor: Admin) -> dict[str, str]:
    return await clearinghouse_settings.read_host_key(db, actor, link, body.host, body.port)


@router.post(f"{CLEARINGHOUSE}/test", response_model=ConnectionCheck)
async def check(db: Db, link: Link, actor: Admin) -> dict[str, bool]:
    return await clearinghouse_settings.check_connection(db, actor, link)


@router.get(CHARGES, response_model=ChargeList)
async def charges(actor: Admin) -> dict[str, Any]:
    return charge_schedule.charge_list(actor.own_practice)


@router.put(f"{CHARGES}/{{code}}", response_model=ChargeList)
async def set_charge(code: str, body: ChargeBody, db: Db, actor: Admin) -> dict[str, Any]:
    return await charge_schedule.set_charge(db, actor, code, body.cents)


@router.delete(f"{CHARGES}/{{code}}", response_model=ChargeList)
async def remove_charge(code: str, db: Db, actor: Admin) -> dict[str, Any]:
    return await charge_schedule.remove_charge(db, actor, code)


@router.post(f"{CHARGES}/import", response_model=ChargeList)
async def import_charges(body: ImportBody, db: Db, actor: Admin) -> dict[str, Any]:
    return await charge_schedule.import_charges(db, actor, body.csv)
