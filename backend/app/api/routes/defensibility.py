from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.routes.billing import INSIGHT_PERIODS
from app.codes.em_benchmarks import EmBenchmarks, default_em_benchmarks
from app.core.calendar import today_in
from app.core.deps import Actor, Db, require
from app.core.errors import Invalid
from app.core.roles import COMPLIANCE, INSIGHT_READERS, NOTE_READERS
from app.services import day_checks, defense_packet, em_mix

router = APIRouter(tags=["defensibility"])
Reader = Annotated[Actor, Depends(require(*NOTE_READERS))]


def em_benchmark_data() -> EmBenchmarks:
    return default_em_benchmarks()


Benchmarks = Annotated[EmBenchmarks, Depends(em_benchmark_data)]


@router.get("/notes/{note_id}/defense-packet")
async def packet(note_id: str, db: Db, actor: Reader) -> Response:
    built = await defense_packet.defense_packet(db, actor, note_id)
    disposition = f'attachment; filename="{built.file_name}"'
    return Response(built.content, media_type="application/pdf", headers={"Content-Disposition": disposition})


@router.get("/notes/{note_id}/day")
async def note_day(note_id: str, db: Db, actor: Reader) -> dict[str, Any]:
    return await day_checks.note_day(db, actor, note_id)


@router.get("/compliance/days")
async def flagged_days(
    db: Db,
    actor: Annotated[Actor, Depends(require(*COMPLIANCE))],
    start: Annotated[date | None, Query(alias="from")] = None,
    end: Annotated[date | None, Query(alias="to")] = None,
) -> dict[str, Any]:
    return await day_checks.flagged_days(db, actor, start, end)


@router.get("/insights/em-mix")
async def level_mix(
    db: Db,
    actor: Annotated[Actor, Depends(require(*INSIGHT_READERS))],
    benchmarks: Benchmarks,
    days: int = 30,
) -> dict[str, Any]:
    if days not in INSIGHT_PERIODS:
        raise Invalid(f"days must be one of {', '.join(str(period) for period in INSIGHT_PERIODS)}")
    end = today_in(actor.zone)
    start = end - timedelta(days=days - 1)
    return await em_mix.em_mix(db, actor.practice_id, benchmarks, start=start, end=end)
