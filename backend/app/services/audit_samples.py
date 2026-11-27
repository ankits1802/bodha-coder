from __future__ import annotations

import random
import secrets
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.billing_codes import Code
from app.core.deps import Actor
from app.core.errors import Invalid, NotFound
from app.core.roles import NOTE_READERS
from app.models import AuditRun, AuditSample, Note, PracticeMembership, Provider, User
from app.services.agreement import elements_of, summarize, visit_agreement
from app.services.analysis import latest_codes
from app.services.audit_log import record_access, record_activity
from app.services.inbox import Notice, notify
from app.services.memberships import active_members, member_names
from app.services.placement import SETTLED_STATUSES, current_findings
from app.services.routing import choices_for, claim

__all__ = [
    "DEFAULT_SAMPLE_SIZE",
    "SPECIALTY_SAMPLE_SIZE",
    "Names",
    "SampleRequest",
    "draw_sample",
    "practice_names",
    "reference_elements",
    "run_items",
    "sample_options",
    "sample_overview",
    "sample_results",
    "samples_overview",
]

DEFAULT_SAMPLE_SIZE = 40
SPECIALTY_SAMPLE_SIZE = 150
SEED_BITS = 63
TRAINING = "training"
TRAINING_ASSIGNED = "training_assigned"
STARTED = {"audit": "started blind audit", TRAINING: "assigned training set"}


@dataclass(frozen=True)
class SampleRequest:
    purpose: str
    scope: str
    start: date
    end: date
    reviewer_ids: tuple[str, ...]
    size: int | None = None
    provider_id: str | None = None
    specialty: str | None = None

    @property
    def wanted(self) -> int:
        if self.size is not None:
            return self.size
        return SPECIALTY_SAMPLE_SIZE if self.scope == "specialty" else DEFAULT_SAMPLE_SIZE


@dataclass(frozen=True)
class Names:
    users: dict[str, str]
    providers: dict[str, str]


async def draw_sample(db: AsyncSession, actor: Actor, request: SampleRequest) -> str:
    _check_request(request)
    reviewers = await _reviewers(db, actor.practice_id, request.reviewer_ids)
    candidates = await _candidates(db, actor.practice_id, request)
    seed = secrets.randbits(SEED_BITS)
    chosen = _assign(candidates, reviewers, request.wanted, random.Random(seed))
    if not chosen:
        raise Invalid("no approved notes match that period")
    run = _new_run(actor, request)
    db.add(run)
    await db.flush()
    for position, (note, reviewer_id) in enumerate(chosen):
        db.add(
            AuditSample(
                practice_id=actor.practice_id,
                note_id=note.id,
                analysis_id=note.current_analysis_id,
                reviewer_id=reviewer_id,
                run_id=run.id,
                purpose=request.purpose,
                status="open",
                answer={},
                result={"position": position, "reference": await _reference(db, note)},
            )
        )
    detail = f"{len(chosen)} notes, seed {seed}"
    record_activity(db, actor, STARTED[request.purpose], practice_id=actor.practice_id, detail=detail)
    if request.purpose == TRAINING:
        await _tell_trainees(db, actor, run.id, Counter(reviewer for _, reviewer in chosen))
    await db.commit()
    return run.id


async def _tell_trainees(db: AsyncSession, actor: Actor, run_id: str, notes_by_trainee: Counter[str]) -> None:
    for trainee, notes in notes_by_trainee.items():
        notice = Notice(TRAINING_ASSIGNED, actor.user.name, actor.user.id, payload={"run_id": run_id, "notes": notes})
        await notify(db, actor.practice_id, [trainee], notice)


def reference_elements(item: AuditSample, side: str) -> dict[str, Any]:
    return elements_of(Code.from_json(code) for code in item.result["reference"][side]).as_json()


async def run_items(db: AsyncSession, practice_id: str, run_id: str) -> tuple[AuditRun, list[AuditSample]]:
    run = await db.get(AuditRun, run_id)
    if run is None or run.practice_id != practice_id:
        raise NotFound("sample not found")
    rows = await db.scalars(select(AuditSample).where(AuditSample.run_id == run.id))
    return run, sorted(rows.all(), key=lambda item: int(item.result.get("position", 0)))


async def practice_names(db: AsyncSession, practice_id: str) -> Names:
    providers = (await db.execute(select(Provider.id, Provider.name).where(Provider.practice_id == practice_id))).all()
    return Names(await member_names(db, practice_id), dict(providers))


async def sample_options(db: AsyncSession, actor: Actor) -> dict[str, Any]:
    providers = list(
        await db.scalars(
            select(Provider)
            .where(Provider.practice_id == actor.practice_id, Provider.active.is_(True))
            .order_by(Provider.name)
        )
    )
    reviewers = await db.execute(
        active_members(actor.practice_id, User.id, User.name, PracticeMembership.role, roles=NOTE_READERS).order_by(
            User.name
        )
    )
    return {
        "providers": [{"id": item.id, "name": item.name, "specialty": item.specialty} for item in providers],
        "reviewers": [{"id": user_id, "name": name, "role": role} for user_id, name, role in reviewers.tuples()],
        "specialties": sorted({item.specialty for item in providers if item.specialty}),
        "default_size": DEFAULT_SAMPLE_SIZE,
        "specialty_size": SPECIALTY_SAMPLE_SIZE,
    }


async def samples_overview(db: AsyncSession, actor: Actor, purpose: str) -> list[dict[str, Any]]:
    runs = list(
        await db.scalars(
            select(AuditRun)
            .where(AuditRun.practice_id == actor.practice_id, AuditRun.purpose == purpose)
            .order_by(AuditRun.created_at.desc())
        )
    )
    items = await db.scalars(select(AuditSample).where(AuditSample.run_id.in_([run.id for run in runs])))
    groups: dict[str, list[AuditSample]] = defaultdict(list)
    for item in items:
        groups[str(item.run_id)].append(item)
    names = await practice_names(db, actor.practice_id)
    return [sample_overview(run, groups[run.id], names) for run in runs]


def sample_overview(run: AuditRun, items: Sequence[AuditSample], names: Names) -> dict[str, Any]:
    done = [item for item in items if item.status == "done"]
    return {
        "id": run.id,
        "purpose": run.purpose,
        "scope": run.scope,
        "provider_name": names.providers.get(run.provider_id or ""),
        "specialty": run.specialty,
        "start": _day(run.period_start),
        "end": _day(run.period_end),
        "requested": run.requested,
        "notes": len(items),
        "done": len(done),
        "status": run.status,
        "reviewers": sorted({names.users.get(item.reviewer_id, "") for item in items}),
        "started_by": names.users.get(run.created_by),
        "started_at": run.created_at.isoformat(),
        "completed_at": _latest(item.completed_at for item in done) if run.status == "done" else None,
        "em": visit_agreement([item.result["bodha"] for item in done]),
        "em_claim": visit_agreement([item.result["claim"] for item in done]),
    }


async def sample_results(db: AsyncSession, actor: Actor, run_id: str) -> dict[str, Any]:
    run, items = await run_items(db, actor.practice_id, run_id)
    names = await practice_names(db, actor.practice_id)
    notes = {note.id: note for note in await db.scalars(select(Note).where(Note.id.in_([i.note_id for i in items])))}
    done = [item for item in items if item.status == "done"]
    record_access(db, actor, "opened audit results", detail=f"{len(items)} notes")
    await db.commit()
    return {
        "sample": sample_overview(run, items, names),
        "summary": _summaries(done),
        "providers": _by_provider(done, notes, names),
        "items": [_item_row(item, notes[item.note_id], names) for item in items],
    }


def _summaries(done: Sequence[AuditSample]) -> dict[str, Any]:
    return {side: summarize([item.result[side] for item in done]) for side in ("bodha", "claim")}


def _by_provider(done: Sequence[AuditSample], notes: dict[str, Note], names: Names) -> list[dict[str, Any]]:
    groups: dict[str, list[AuditSample]] = defaultdict(list)
    for item in done:
        groups[notes[item.note_id].provider_id].append(item)
    rows = [
        {"provider_id": provider_id, "provider_name": names.providers.get(provider_id, ""), **_summaries(items)}
        for provider_id, items in groups.items()
    ]
    return sorted(rows, key=lambda row: row["provider_name"])


def _item_row(item: AuditSample, note: Note, names: Names) -> dict[str, Any]:
    done = item.status == "done"
    return {
        "id": item.id,
        "position": int(item.result.get("position", 0)) + 1,
        "provider_name": names.providers.get(note.provider_id, ""),
        "service_date": note.service_date.isoformat(),
        "reviewer_name": names.users.get(item.reviewer_id, ""),
        "status": item.status,
        "answer": {key: item.answer.get(key) for key in ("em", "icd", "modifiers")} if done else None,
        "bodha": reference_elements(item, "bodha") if done else None,
        "claim": reference_elements(item, "claim") if done else None,
        "agreement": {"bodha": item.result["bodha"], "claim": item.result["claim"]} if done else None,
    }


def _latest(moments: Iterable[datetime | None]) -> str | None:
    known = [moment for moment in moments if moment is not None]
    return max(known).isoformat() if known else None


def _day(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _check_request(request: SampleRequest) -> None:
    if request.start > request.end:
        raise Invalid("the period ends before it starts")
    if request.scope == "provider" and not request.provider_id:
        raise Invalid("choose a provider")
    if request.scope == "specialty" and not request.specialty:
        raise Invalid("choose a specialty")
    if not request.reviewer_ids:
        raise Invalid("choose at least one reviewer")


async def _reviewers(db: AsyncSession, practice_id: str, reviewer_ids: tuple[str, ...]) -> list[str]:
    wanted = list(dict.fromkeys(reviewer_ids))
    found = set(await db.scalars(active_members(practice_id, User.id, roles=NOTE_READERS).where(User.id.in_(wanted))))
    missing = [reviewer for reviewer in wanted if reviewer not in found]
    if missing:
        raise Invalid("choose reviewers from the active team")
    return wanted


async def _candidates(db: AsyncSession, practice_id: str, request: SampleRequest) -> list[Note]:
    query = (
        select(Note)
        .where(
            Note.practice_id == practice_id,
            Note.status.in_(SETTLED_STATUSES),
            Note.service_date >= request.start,
            Note.service_date <= request.end,
        )
        .order_by(Note.id)
    )
    if request.scope == "provider":
        provider = await db.get(Provider, request.provider_id)
        if provider is None or provider.practice_id != practice_id:
            raise Invalid("choose a provider of this practice")
        query = query.where(Note.provider_id == provider.id)
    if request.scope == "specialty":
        query = query.join(Provider, Provider.id == Note.provider_id).where(Provider.specialty == request.specialty)
    return list((await db.scalars(query)).all())


def _assign(candidates: list[Note], reviewers: list[str], wanted: int, rng: random.Random) -> list[tuple[Note, str]]:
    order = list(candidates)
    rng.shuffle(order)
    chosen: list[tuple[Note, str]] = []
    turn = 0
    for note in order:
        if len(chosen) == wanted:
            break
        reviewer = _next_reviewer(reviewers, turn, note.approved_by)
        if reviewer is None:
            continue
        chosen.append((note, reviewer))
        turn = reviewers.index(reviewer) + 1
    return chosen


def _next_reviewer(reviewers: list[str], turn: int, approver: str | None) -> str | None:
    for offset in range(len(reviewers)):
        reviewer = reviewers[(turn + offset) % len(reviewers)]
        if reviewer != approver:
            return reviewer
    return None


def _new_run(actor: Actor, request: SampleRequest) -> AuditRun:
    return AuditRun(
        practice_id=actor.practice_id,
        created_by=actor.user.id,
        purpose=request.purpose,
        scope=request.scope,
        provider_id=request.provider_id if request.scope == "provider" else None,
        specialty=request.specialty if request.scope == "specialty" else None,
        period_start=request.start,
        period_end=request.end,
        requested=request.wanted,
        status="open",
    )


async def _reference(db: AsyncSession, note: Note) -> dict[str, list[dict[str, object]]]:
    findings = await current_findings(db, note)
    suggested = claim(await latest_codes(db, note.id, "billed"), findings, choices_for(findings, {}))
    final = await latest_codes(db, note.id, "final")
    return {"bodha": [code.as_json() for code in suggested], "claim": [code.as_json() for code in final]}
