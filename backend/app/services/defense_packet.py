from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore
from app.adapters.pdf_writer import render_pdf
from app.codes.billing_codes import Code
from app.codes.catalog_pfs import DATA_YEAR as PFS_CODE_YEAR
from app.codes.catalog_pfs import MLN_EDITION
from app.codes.icd import fiscal_year_for
from app.core.deps import Actor
from app.models import (
    AccessLog,
    AddendumRequest,
    Analysis,
    CodeSet,
    Decision,
    Note,
    PlaceOfService,
    Provider,
    User,
    utcnow,
)
from app.services.analysis import latest_codes
from app.services.audit_log import record_access
from app.services.certificates import note_certificates
from app.services.defense_layout import (
    CHOICE_LABELS,
    DecidedFinding,
    PacketEvent,
    PacketFacts,
    PacketRequest,
    PacketVisit,
    packet_document,
)
from app.services.defense_records import packet_records
from app.services.estimates import claim_estimate
from app.services.finding import Finding
from app.services.override_reasons import reason_text
from app.services.placement import SETTLED_STATUSES, current_findings
from app.services.pointer_decisions import read_pointer_key
from app.services.review_actions import current_claim, note_for
from app.services.risk_adjustment import RISK_SUMMARY_KEY
from app.services.routing import CHANGE_KINDS, choices_for

__all__ = ["DECIDED_CHOICES", "HISTORY_ACTIONS", "DefensePacket", "build_packet", "defense_packet", "packet_file_name"]

DECIDED_CHOICES = ("accept", "keep", "add")
HISTORY_ACTIONS = (
    "approved",
    "asked provider",
    "asked provider to confirm level",
    "cancelled provider request",
    "changed visit type",
    "compliance confirm",
    "compliance keep",
    "confirmed visit level",
    "disagreed with visit level",
    "edited billed codes",
    "flagged for compliance",
    "linked diagnoses",
    "override reason",
    "reopened",
    "reopened after disagreement",
    "replaced PDF",
    "returned to coder",
    "signed addendum",
)
DOWNLOADED = "downloaded defense packet"


@dataclass(frozen=True)
class DefensePacket:
    file_name: str
    content: bytes


def packet_file_name(note: Note) -> str:
    return f"bodha-defense-packet-{note.service_date:%Y%m%d}-{note.id[:8]}.pdf"


async def defense_packet(db: AsyncSession, store: ObjectStore, actor: Actor, note_id: str) -> DefensePacket:
    note = await note_for(db, actor, note_id)
    packet = await build_packet(db, store, actor, note)
    record_access(db, actor, DOWNLOADED, note_id=note.id)
    await db.commit()
    return packet


async def build_packet(db: AsyncSession, store: ObjectStore, actor: Actor, note: Note) -> DefensePacket:
    facts = await _facts(db, store, actor, note)
    content = await asyncio.to_thread(render_pdf, packet_document(facts))
    return DefensePacket(packet_file_name(note), content)


async def _facts(db: AsyncSession, store: ObjectStore, actor: Actor, note: Note) -> PacketFacts:
    provider = await db.get_one(Provider, note.provider_id)
    names = dict((await db.execute(select(User.id, User.name).where(User.practice_id == note.practice_id))).all())
    findings = await current_findings(db, note)
    decisions = list(
        (await db.scalars(select(Decision).where(Decision.note_id == note.id).order_by(Decision.created_at))).all()
    )
    analyses = list(
        (await db.scalars(select(Analysis).where(Analysis.note_id == note.id).order_by(Analysis.revision))).all()
    )
    settled = note.status in SETTLED_STATUSES
    claim = await latest_codes(db, note.id, "final") if settled else await current_claim(db, note)
    visit = _visit(note, provider, await db.get(PlaceOfService, note.place_code), actor)
    current = next((row for row in analyses if row.id == note.current_analysis_id), None)
    return PacketFacts(
        zone=actor.zone,
        visit=visit,
        approved=_approval(note, names) if settled else None,
        claim=claim,
        billed=await latest_codes(db, note.id, "billed"),
        estimate=claim_estimate(claim, note.place_code, note.service_date),
        em=next((item for item in findings if item.kind == "em"), None),
        decided=_decided(findings, decisions, names),
        checks=_checks(note, findings),
        requests=await _requests(db, note, visit.provider_label, names),
        history=await _history(db, note, findings, decisions, names),
        analyses=tuple(_analysis_row(row, note) for row in analyses),
        analysis_label=_analysis_label(current),
        generated=PacketEvent(utcnow(), actor.user.name, DOWNLOADED),
        records=await packet_records(db, note, findings, decisions, names),
        certificates=tuple(await note_certificates(db, store, note.id)),
    )


def _visit(note: Note, provider: Provider, place: PlaceOfService | None, actor: Actor) -> PacketVisit:
    return PacketVisit(
        practice_name=actor.own_practice.name,
        provider_label=f"{provider.name}, {provider.credential}",
        provider_npi=provider.npi,
        provider_specialty=provider.specialty,
        place=f"{place.name} ({note.place_code})" if place else note.place_code,
        patient_name=note.patient_name,
        patient_age=note.patient_age,
        patient_sex=note.patient_sex,
        service_date=note.service_date,
        visit_type=note.visit_type,
    )


def _approval(note: Note, names: Mapping[str, str]) -> PacketEvent | None:
    if note.approved_at is None or note.approved_by is None:
        return None
    return PacketEvent(note.approved_at, names.get(note.approved_by, ""), "approved")


def _decided(
    findings: list[Finding], decisions: Sequence[Decision], names: Mapping[str, str]
) -> tuple[DecidedFinding, ...]:
    latest = {row.suggestion_key: row for row in decisions}
    choices = choices_for(findings, {key: row.choice for key, row in latest.items()})
    decided = []
    for finding in findings:
        if (
            finding.kind not in CHANGE_KINDS
            or finding.key == RISK_SUMMARY_KEY
            or choices[finding.key] not in DECIDED_CHOICES
        ):
            continue
        row = latest.get(finding.key)
        by = names.get(row.actor_id) if row else None
        reason = reason_text(row.override_reason, row.override_note) if row else None
        decided.append(DecidedFinding(finding, choices[finding.key], by, row.created_at if row else None, reason))
    return tuple(decided)


def _checks(note: Note, findings: list[Finding]) -> tuple[tuple[str, str], ...]:
    checks = [
        ("ICD-10-CM", f"FY{fiscal_year_for(note.service_date)} release (CDC) for the date of service"),
        ("CPT and HCPCS", f"CMS physician fee schedule code list, {PFS_CODE_YEAR}"),
        ("E/M levels", f"AMA CPT E/M descriptors; CMS MLN006764, {MLN_EDITION}"),
    ]
    risk = next((item for item in findings if item.key == RISK_SUMMARY_KEY), None)
    if risk is not None:
        detail: dict[str, Any] = risk.detail
        state = "" if detail.get("available") else ", not available"
        checks.append(
            (
                "Risk adjustment",
                f"{detail.get('model', 'CMS-HCC V28')}, payment year {detail.get('payment_year')}{state}",
            )
        )
    return tuple(checks)


async def _requests(
    db: AsyncSession, note: Note, provider_label: str, names: Mapping[str, str]
) -> tuple[PacketRequest, ...]:
    rows = await db.scalars(
        select(AddendumRequest).where(AddendumRequest.note_id == note.id).order_by(AddendumRequest.created_at)
    )
    return tuple(
        PacketRequest(
            sent_at=row.created_at,
            sent_by=names.get(row.sent_by, ""),
            channel=row.channel,
            status=row.status,
            answers=_answers(row),
            addendum_text=row.addendum_text,
            signed_at=row.answered_at,
            provider_label=provider_label,
        )
        for row in rows
    )


def _answers(request: AddendumRequest) -> tuple[tuple[str, str], ...]:
    answers = {item["key"]: item for item in request.answers or []}
    rows = []
    for question in request.questions:
        answer = answers.get(question["key"])
        reply = " · ".join(part for part in (answer.get("choice"), answer.get("comment")) if part) if answer else "—"
        rows.append((question["text"], reply))
    return tuple(rows)


def _decision_text(row: Decision, titles: Mapping[str, str]) -> str:
    reason = reason_text(row.override_reason, row.override_note)
    return " · ".join(part for part in (_decision_subject(row, titles), reason and f"Reason: {reason}") if part)


def _decision_subject(row: Decision, titles: Mapping[str, str]) -> str:
    parsed = read_pointer_key(row.suggestion_key)
    if parsed is None:
        return f"{CHOICE_LABELS.get(row.choice, row.choice)} · {titles.get(row.suggestion_key, row.suggestion_key)}"
    code, diagnoses = parsed
    return f"Linked {code} to {', '.join(diagnoses)}" if diagnoses else f"Linked {code} to the default diagnoses"


async def _history(
    db: AsyncSession, note: Note, findings: list[Finding], decisions: Sequence[Decision], names: Mapping[str, str]
) -> tuple[PacketEvent, ...]:
    titles = {finding.key: finding.title for finding in findings}
    events = [
        PacketEvent(
            row.created_at,
            names.get(row.actor_id, ""),
            _decision_text(row, titles),
        )
        for row in decisions
    ]
    code_sets = await db.scalars(select(CodeSet).where(CodeSet.note_id == note.id).order_by(CodeSet.created_at))
    events += [
        PacketEvent(row.created_at, names.get(row.actor_id or "", "Bodha"), _code_set_text(row)) for row in code_sets
    ]
    access = await db.scalars(
        select(AccessLog)
        .where(AccessLog.note_id == note.id, AccessLog.action.in_(HISTORY_ACTIONS))
        .order_by(AccessLog.created_at)
    )
    events += [
        PacketEvent(row.created_at, row.actor_name, " · ".join(filter(None, (row.action, row.detail))))
        for row in access
    ]
    return tuple(sorted(events, key=lambda event: event.at))


def _code_set_text(row: CodeSet) -> str:
    codes = ", ".join(Code.from_json(item).label() for item in row.codes)
    reason = reason_text(row.override_reason, row.override_note)
    text = f"{row.kind.capitalize()} codes, revision {row.revision} ({row.reason}): {codes}"
    return f"{text} · Reason: {reason}" if reason else text


def _analysis_row(row: Analysis, note: Note) -> tuple[str, ...]:
    current = " (current)" if row.id == note.current_analysis_id else ""
    finished = row.finished_at.strftime("%Y-%m-%d %H:%M UTC") if row.finished_at else "—"
    return (f"{row.revision}{current}", row.reason, row.status, row.model or "—", row.prompt_version or "—", finished)


def _analysis_label(row: Analysis | None) -> str:
    if row is None:
        return "Not read yet"
    return f"Run {row.revision}, model {row.model or 'unknown'}, prompt version {row.prompt_version or 'unknown'}"
