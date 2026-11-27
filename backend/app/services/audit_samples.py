from __future__ import annotations

import random
import secrets
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.billing_codes import Code
from app.core.deps import Actor
from app.core.errors import Invalid, NotFound
from app.core.roles import NOTE_READERS
from app.models import AuditSample, Note, Provider, User, new_id, utcnow
from app.services.agreement import elements_of, summarize
from app.services.analysis import latest_codes
from app.services.audit_log import record_access, record_activity
from app.services.placement import SETTLED_STATUSES, current_findings
from app.services.routing import choices_for, claim
from app.services.samples import SAMPLE_ID_PATH, sample_id_of

__all__ = [
    "DEFAULT_SAMPLE_SIZE",
    "SPECIALTY_SAMPLE_SIZE",
    "Names",
    "SampleRequest",
    "draw_sample",
    "practice_names",
    "reference_elements",
    "sample_overview",
    "sample_options",
    "sample_results",
    "sample_rows",
    "samples_overview",
]

DEFAULT_SAMPLE_SIZE = 40
SPECIALTY_SAMPLE_SIZE = 150
SEED_BITS = 63
STARTED = {"audit": "started blind audit", "training": "assigned training set"}


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
    meta = _meta(actor, request, seed)
    for position, (note, reviewer_id) in enumerate(chosen):
        db.add(
            AuditSample(
                practice_id=actor.practice_id,
                note_id=note.id,
                analysis_id=note.current_analysis_id,
                reviewer_id=reviewer_id,
                purpose=request.purpose,
                status="open",
                answer={},
                result={"sample": meta, "position": position, "reference": await _reference(db, note)},
            )
        )
    record_activity(db, actor, STARTED[request.purpose], practice_id=actor.practice_id, detail=f"{len(chosen)} notes")
    await db.commit()
    return meta["id"]


def reference_elements(item: AuditSample, side: str) -> dict[str, Any]:
    return elements_of(Code.from_json(code) for code in item.result["reference"][side]).as_json()


async def sample_rows(db: AsyncSession, practice_id: str, sample_id: str) -> list[AuditSample]:
    rows = await db.scalars(
        select(AuditSample).where(
            AuditSample.practice_id == practice_id, AuditSample.result[SAMPLE_ID_PATH].astext == sample_id
        )
    )
    found = sorted(rows.all(), key=lambda item: int(item.result.get("position", 0)))
    if not found:
        raise NotFound("sample not found")
    return found


async def practice_names(db: AsyncSession, practice_id: str) -> Names:
    users = (await db.execute(select(User.id, User.name).where(User.practice_id == practice_id))).all()
    providers = (await db.execute(select(Provider.id, Provider.name).where(Provider.practice_id == practice_id))).all()
    return Names(dict(users), dict(providers))


async def sample_options(db: AsyncSession, actor: Actor) -> dict[str, Any]:
    providers = list(
        await db.scalars(
            select(Provider)
            .where(Provider.practice_id == actor.practice_id, Provider.active.is_(True))
            .order_by(Provider.name)
        )
    )
    reviewers = await db.scalars(
        select(User)
        .where(User.practice_id == actor.practice_id, User.status == "active", User.role.in_(NOTE_READERS))
        .order_by(User.name)
    )
    return {
        "providers": [{"id": item.id, "name": item.name, "specialty": item.specialty} for item in providers],
        "reviewers": [{"id": user.id, "name": user.name, "role": user.role} for user in reviewers],
        "specialties": sorted({item.specialty for item in providers if item.specialty}),
        "default_size": DEFAULT_SAMPLE_SIZE,
        "specialty_size": SPECIALTY_SAMPLE_SIZE,
    }


async def samples_overview(db: AsyncSession, actor: Actor, purpose: str) -> list[dict[str, Any]]:
    rows = await db.scalars(
        select(AuditSample)
        .where(AuditSample.practice_id == actor.practice_id, AuditSample.purpose == purpose)
        .order_by(AuditSample.created_at.desc())
    )
    groups: dict[str, list[AuditSample]] = defaultdict(list)
    for item in rows:
        groups[sample_id_of(item)].append(item)
    names = await practice_names(db, actor.practice_id)
    return [sample_overview(items, names) for items in groups.values()]


def sample_overview(items: Sequence[AuditSample], names: Names) -> dict[str, Any]:
    meta = items[0].result["sample"]
    done = [item for item in items if item.status == "done"]
    finished = len(done) == len(items)
    return {
        "id": meta["id"],
        "purpose": meta["purpose"],
        "scope": meta["scope"],
        "provider_name": names.providers.get(meta.get("provider_id") or ""),
        "specialty": meta.get("specialty"),
        "start": meta["start"],
        "end": meta["end"],
        "requested": meta["requested"],
        "notes": len(items),
        "done": len(done),
        "status": "done" if finished else "open",
        "reviewers": sorted({names.users.get(item.reviewer_id, "") for item in items}),
        "started_at": meta["started_at"],
        "completed_at": max(_completed(item) for item in done) if finished else None,
        "em": summarize([item.result["bodha"] for item in done])["em"],
        "em_claim": summarize([item.result["claim"] for item in done])["em"],
    }


async def sample_results(db: AsyncSession, actor: Actor, sample_id: str) -> dict[str, Any]:
    items = await sample_rows(db, actor.practice_id, sample_id)
    names = await practice_names(db, actor.practice_id)
    notes = {note.id: note for note in await db.scalars(select(Note).where(Note.id.in_([i.note_id for i in items])))}
    done = [item for item in items if item.status == "done"]
    record_access(db, actor, "opened audit results", detail=f"{len(items)} notes")
    await db.commit()
    return {
        "sample": sample_overview(items, names),
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


def _completed(item: AuditSample) -> str:
    return item.completed_at.isoformat() if item.completed_at else ""


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
    found = set(
        await db.scalars(
            select(User.id).where(
                User.id.in_(wanted),
                User.practice_id == practice_id,
                User.status == "active",
                User.role.in_(NOTE_READERS),
            )
        )
    )
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


def _meta(actor: Actor, request: SampleRequest, seed: int) -> dict[str, Any]:
    return {
        "id": new_id(),
        "purpose": request.purpose,
        "scope": request.scope,
        "provider_id": request.provider_id if request.scope == "provider" else None,
        "specialty": request.specialty if request.scope == "specialty" else None,
        "start": request.start.isoformat(),
        "end": request.end.isoformat(),
        "requested": request.wanted,
        "seed": str(seed),
        "started_by": actor.user.id,
        "started_at": utcnow().isoformat(),
    }


async def _reference(db: AsyncSession, note: Note) -> dict[str, list[dict[str, object]]]:
    findings = await current_findings(db, note)
    suggested = claim(await latest_codes(db, note.id, "billed"), findings, choices_for(findings, {}))
    final = await latest_codes(db, note.id, "final")
    return {"bodha": [code.as_json() for code in suggested], "claim": [code.as_json() for code in final]}
