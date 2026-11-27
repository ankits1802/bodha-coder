from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.quality_bodies import AutoApproveBody, EvalCaseBody, SampleBody
from app.api.responses.base import Created, ExactRoute
from app.api.responses.evaluations import (
    EvalCandidateList,
    EvalCaseAdded,
    EvalCaseList,
    EvalRunDetail,
    EvalRuns,
    EvalRunView,
)
from app.api.responses.quality import (
    LevelMix,
    ProviderAutonomy,
    ProviderAutonomyList,
    QualityOptions,
    SampleList,
    SampleResults,
)
from app.core.deps import Actor, Db, require
from app.core.roles import ADMINS, COMPLIANCE
from app.services import audit_samples, autonomy, evaluation_set, level_mix
from app.services.audit_samples import SampleRequest

router = APIRouter(prefix="/quality", tags=["quality"], route_class=ExactRoute)
Overseer = Annotated[Actor, Depends(require(*COMPLIANCE))]
Admin = Annotated[Actor, Depends(require(*ADMINS))]


@router.get("/options", response_model=QualityOptions)
async def options(db: Db, actor: Overseer) -> dict[str, Any]:
    return await audit_samples.sample_options(db, actor)


@router.get("/samples", response_model=SampleList)
async def samples(db: Db, actor: Overseer) -> dict[str, Any]:
    return {"items": await audit_samples.samples_overview(db, actor, "audit")}


@router.post("/samples", response_model=Created)
async def start_sample(body: SampleBody, db: Db, actor: Overseer) -> dict[str, str]:
    request = SampleRequest(
        purpose="audit",
        scope=body.scope,
        start=body.start,
        end=body.end,
        reviewer_ids=tuple(body.reviewer_ids),
        size=body.size,
        provider_id=body.provider_id,
        specialty=body.specialty,
    )
    return {"id": await audit_samples.draw_sample(db, actor, request)}


@router.get("/samples/{sample_id}", response_model=SampleResults)
async def sample_results(sample_id: str, db: Db, actor: Overseer) -> dict[str, Any]:
    return await audit_samples.sample_results(db, actor, sample_id)


@router.get("/providers", response_model=ProviderAutonomyList)
async def providers(db: Db, actor: Overseer) -> dict[str, Any]:
    return {"items": await autonomy.providers_autonomy(db, actor)}


@router.put("/providers/{provider_id}/auto-approve", response_model=ProviderAutonomy)
async def auto_approve(provider_id: str, body: AutoApproveBody, db: Db, actor: Admin) -> dict[str, Any]:
    return await autonomy.set_auto_approve(db, actor, provider_id, on=body.on)


@router.get("/level-mix", response_model=LevelMix)
async def level_mix_drift(db: Db, actor: Overseer) -> dict[str, Any]:
    return await level_mix.level_mix(db, actor)


@router.get("/evaluations", response_model=EvalRuns)
async def evaluations(db: Db, actor: Overseer) -> dict[str, Any]:
    return await evaluation_set.evaluation_runs(db, actor)


@router.post("/evaluations", response_model=EvalRunView)
async def run_evaluation(db: Db, actor: Admin) -> dict[str, Any]:
    return await evaluation_set.queue_run(db, actor)


@router.get("/evaluations/{run_id}", response_model=EvalRunDetail)
async def evaluation(run_id: str, db: Db, actor: Overseer) -> dict[str, Any]:
    return await evaluation_set.run_detail(db, actor, run_id)


@router.get("/eval-cases", response_model=EvalCaseList)
async def eval_cases(db: Db, actor: Overseer) -> dict[str, Any]:
    return {"items": await evaluation_set.evaluation_cases(db, actor)}


@router.get("/eval-cases/candidates", response_model=EvalCandidateList)
async def eval_candidates(db: Db, actor: Admin) -> dict[str, Any]:
    return {"items": await evaluation_set.case_candidates(db, actor)}


@router.post("/eval-cases", response_model=EvalCaseAdded)
async def add_eval_case(body: EvalCaseBody, db: Db, actor: Admin) -> dict[str, Any]:
    return await evaluation_set.mark_case(db, actor, body.note_id)


@router.delete("/eval-cases/{note_id}", status_code=204)
async def remove_eval_case(note_id: str, db: Db, actor: Admin) -> None:
    await evaluation_set.remove_case(db, actor, note_id)
