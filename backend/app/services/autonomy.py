from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor
from app.core.errors import Conflict, NotFound
from app.core.statistics import wilson
from app.models import AuditRun, AuditSample, Note, Provider
from app.services.audit_log import record_activity

__all__ = [
    "MAX_BODHA_HIGHER_SHARE",
    "MIN_AUDIT_NOTES",
    "MIN_EM_LOWER_BOUND",
    "Eligibility",
    "provider_eligibility",
    "providers_autonomy",
    "set_auto_approve",
]

MIN_AUDIT_NOTES = 30
MIN_EM_LOWER_BOUND = 0.90
MAX_BODHA_HIGHER_SHARE = 0.05
REFUSALS = {
    "no_audit": "complete a blind audit of this provider's notes first",
    "too_few_notes": f"the latest blind audit has fewer than {MIN_AUDIT_NOTES} of this provider's notes",
    "agreement_low": "visit-level agreement in the latest blind audit is below the threshold",
    "too_many_higher": "Bodha coded too many visits higher than the auditor",
}


@dataclass(frozen=True)
class Eligibility:
    eligible: bool
    reason: str
    sample_id: str | None = None
    notes: int = 0
    em_low: float | None = None
    higher_share: float | None = None

    def as_json(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "reason": self.reason,
            "sample_id": self.sample_id,
            "notes": self.notes,
            "em_low": self.em_low,
            "higher_share": self.higher_share,
        }


async def provider_eligibility(db: AsyncSession, provider: Provider) -> Eligibility:
    items = await _latest_audit_items(db, provider)
    if not items:
        return Eligibility(False, "no_audit")
    visits = [item.result["bodha"]["em"] for item in items]
    total = len(visits)
    agreement = wilson(sum(visit["match"] for visit in visits), total)
    higher = sum(visit["direction"] == "higher" for visit in visits) / total
    reason = _reason(total, agreement.low, higher)
    return Eligibility(reason == "eligible", reason, items[0].run_id, total, agreement.low, higher)


async def providers_autonomy(db: AsyncSession, actor: Actor) -> list[dict[str, Any]]:
    providers = list(
        await db.scalars(
            select(Provider)
            .where(Provider.practice_id == actor.practice_id, Provider.active.is_(True))
            .order_by(Provider.name)
        )
    )
    return [_provider_view(provider, await provider_eligibility(db, provider)) for provider in providers]


async def set_auto_approve(db: AsyncSession, actor: Actor, provider_id: str, *, on: bool) -> dict[str, Any]:
    provider = await db.get(Provider, provider_id)
    if provider is None or provider.practice_id != actor.practice_id:
        raise NotFound("provider not found")
    eligibility = await provider_eligibility(db, provider)
    if on and not eligibility.eligible:
        raise Conflict(REFUSALS[eligibility.reason])
    provider.auto_approve = on
    action = "auto-approve on" if on else "auto-approve off"
    record_activity(db, actor, action, practice_id=actor.practice_id, detail=provider.name)
    await db.commit()
    return _provider_view(provider, eligibility)


def _provider_view(provider: Provider, eligibility: Eligibility) -> dict[str, Any]:
    return {
        "id": provider.id,
        "name": provider.name,
        "credential": provider.credential,
        "specialty": provider.specialty,
        "auto_approve": provider.auto_approve,
        "eligibility": eligibility.as_json(),
    }


def _reason(total: int, low: float | None, higher: float) -> str:
    if total < MIN_AUDIT_NOTES:
        return "too_few_notes"
    if low is None or low < MIN_EM_LOWER_BOUND:
        return "agreement_low"
    if higher > MAX_BODHA_HIGHER_SHARE:
        return "too_many_higher"
    return "eligible"


async def _latest_audit_items(db: AsyncSession, provider: Provider) -> list[AuditSample]:
    providers_runs = (
        select(AuditSample.run_id).join(Note, Note.id == AuditSample.note_id).where(Note.provider_id == provider.id)
    )
    latest = await db.scalar(
        select(AuditSample.run_id)
        .join(AuditRun, AuditRun.id == AuditSample.run_id)
        .where(
            AuditRun.practice_id == provider.practice_id,
            AuditRun.purpose == "audit",
            AuditRun.status == "done",
            AuditRun.id.in_(providers_runs),
        )
        .group_by(AuditSample.run_id)
        .order_by(func.max(AuditSample.completed_at).desc().nulls_last())
        .limit(1)
    )
    if latest is None:
        return []
    rows = await db.scalars(
        select(AuditSample)
        .join(Note, Note.id == AuditSample.note_id)
        .where(AuditSample.run_id == latest, Note.provider_id == provider.id)
    )
    return list(rows.all())
