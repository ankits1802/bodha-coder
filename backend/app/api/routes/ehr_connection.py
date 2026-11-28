from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.api.ehr_bodies import EhrConnectionBody, EhrKeyBody
from app.api.responses.base import ExactRoute
from app.api.responses.ehr_connection import EhrCheckView, EhrConnectionView, EhrDocumentPage, EhrPullRunPage, JwksView
from app.api.wiring import Outbound
from app.core.deps import Actor, Db, require
from app.core.roles import ADMINS
from app.services.ehr_checks import check_connection
from app.services.ehr_keys import create_key, published_keys
from app.services.ehr_settings import EhrSettings, pause_pulling, resume_pulling, save_connection
from app.services.ehr_views import connection_view, document_page, run_page

router = APIRouter(tags=["ehr connection"], route_class=ExactRoute)
Admin = Annotated[Actor, Depends(require(*ADMINS))]
EHR_CONNECTION = "/practice/ehr-connection"


@router.get(EHR_CONNECTION, response_model=EhrConnectionView)
async def ehr_connection(db: Db, actor: Admin) -> dict[str, Any]:
    return await connection_view(db, actor)


@router.put(EHR_CONNECTION, response_model=EhrConnectionView)
async def save(body: EhrConnectionBody, db: Db, actor: Admin, outbound: Outbound) -> dict[str, Any]:
    settings = EhrSettings(body.base_url, body.client_id, tuple(body.scopes), tuple(body.note_types), body.start_date)
    await save_connection(db, actor, settings, outbound)
    return await connection_view(db, actor)


@router.post(f"{EHR_CONNECTION}/key", response_model=EhrConnectionView)
async def new_key(body: EhrKeyBody, db: Db, actor: Admin) -> dict[str, Any]:
    await create_key(db, actor, body.algorithm)
    return await connection_view(db, actor)


@router.post(f"{EHR_CONNECTION}/pause", response_model=EhrConnectionView)
async def pause(db: Db, actor: Admin) -> dict[str, Any]:
    await pause_pulling(db, actor)
    return await connection_view(db, actor)


@router.post(f"{EHR_CONNECTION}/resume", response_model=EhrConnectionView)
async def resume(db: Db, actor: Admin) -> dict[str, Any]:
    await resume_pulling(db, actor)
    return await connection_view(db, actor)


@router.post(f"{EHR_CONNECTION}/tests", response_model=EhrCheckView)
async def run_check(db: Db, actor: Admin, outbound: Outbound) -> dict[str, Any]:
    return await check_connection(db, actor, outbound)


@router.get(f"{EHR_CONNECTION}/runs", response_model=EhrPullRunPage)
async def runs(db: Db, actor: Admin, offset: Annotated[int, Query(ge=0)] = 0) -> dict[str, Any]:
    return await run_page(db, actor, offset=offset)


@router.get(f"{EHR_CONNECTION}/documents", response_model=EhrDocumentPage)
async def documents(db: Db, actor: Admin, offset: Annotated[int, Query(ge=0)] = 0) -> dict[str, Any]:
    return await document_page(db, actor, offset=offset)


@router.get("/ehr/jwks/{key_set}", response_model=JwksView)
async def jwks(key_set: str, db: Db) -> dict[str, Any]:
    return await published_keys(db, key_set)
