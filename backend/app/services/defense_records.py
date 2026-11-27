from __future__ import annotations

from collections.abc import Mapping, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.billing_codes import Code
from app.models import AccessLog, Analysis, Decision, Note, Provider, Suggestion
from app.services.attestations import note_attestations
from app.services.claim_exports import note_exports
from app.services.claim_snapshots import note_snapshots
from app.services.defense_record_layout import (
    PacketAttestation,
    PacketComment,
    PacketRecords,
    PacketReview,
    PacketRow,
    PacketText,
)
from app.services.finding import Finding
from app.services.note_texts import current_texts, note_texts
from app.services.override_reasons import reason_text
from app.services.review_actions import allowed_choices
from app.services.review_comments import note_comment_rows

__all__ = ["COMPLIANCE_ACTIONS", "packet_records"]

COMPLIANCE_ACTIONS = ("flagged for compliance", "returned to coder", "compliance confirm", "compliance keep")
SHORT_HASH = 12


async def packet_records(
    db: AsyncSession, note: Note, findings: list[Finding], decisions: Sequence[Decision], names: Mapping[str, str]
) -> PacketRecords:
    texts = [text for text in current_texts(await note_texts(db, note.id)) if text.text]
    return PacketRecords(
        texts=tuple(PacketText(text.revision, text.source, text.text) for text in texts),
        not_followed=not_followed(findings, decisions, names),
        earlier=await _earlier(db, note),
        compliance=await _compliance(db, note),
        snapshots=await _snapshots(db, note.id),
        exports=await _exports(db, note.id),
        attestations=await _attestations(db, note.id),
        comments=await _comments(db, note.id),
        flag_reason=note.flag_reason,
    )


def not_followed(
    findings: list[Finding], decisions: Sequence[Decision], names: Mapping[str, str]
) -> tuple[PacketReview, ...]:
    latest = {row.suggestion_key: row for row in decisions}
    reviews = []
    for finding in findings:
        allowed = allowed_choices(finding)
        row = latest.get(finding.key)
        choice = row.choice if row else finding.default_choice
        if len(allowed) < 2 or choice == allowed[0]:
            continue
        reason = reason_text(row.override_reason, row.override_note) if row else None
        by = names.get(row.actor_id) if row else None
        reviews.append(PacketReview(finding, choice, by, row.created_at if row else None, reason))
    return tuple(reviews)


async def _earlier(db: AsyncSession, note: Note) -> tuple[tuple[str, ...], ...]:
    rows = await db.execute(
        select(Analysis.revision, Suggestion)
        .join(Suggestion, Suggestion.analysis_id == Analysis.id)
        .where(Analysis.note_id == note.id, Analysis.id != (note.current_analysis_id or ""))
        .order_by(Analysis.revision, Suggestion.kind, Suggestion.key)
    )
    return tuple(
        (
            str(revision),
            row.kind,
            row.action,
            " → ".join(code for code in (row.code_before, row.code_after) if code) or "—",
            row.title,
        )
        for revision, row in rows.all()
    )


async def _compliance(db: AsyncSession, note: Note) -> tuple[PacketRow, ...]:
    rows = await db.scalars(
        select(AccessLog)
        .where(
            AccessLog.note_id == note.id,
            AccessLog.practice_id == note.practice_id,
            AccessLog.action.in_(COMPLIANCE_ACTIONS),
        )
        .order_by(AccessLog.created_at)
    )
    return tuple(PacketRow(row.created_at, (row.actor_name, row.action, row.detail or "—")) for row in rows)


async def _snapshots(db: AsyncSession, note_id: str) -> tuple[PacketRow, ...]:
    rows = []
    for row in await note_snapshots(db, note_id):
        codes = ", ".join(Code.from_json(item).label() for item in row.content.get("codes", []))
        cells = (
            str(row.revision),
            f"{row.approver_name} ({row.approver_role})",
            codes,
            f"{row.model or '—'} · {row.prompt_version or '—'}",
            row.document_sha256[:SHORT_HASH],
        )
        rows.append(PacketRow(row.approved_at, cells))
    return tuple(rows)


async def _exports(db: AsyncSession, note_id: str) -> tuple[PacketRow, ...]:
    return tuple(
        PacketRow(
            export.created_at,
            (
                f"{export.actor_name} ({export.actor_role})",
                export.format,
                str(export.notes_count),
                str(item.snapshot_revision),
                export.file_sha256[:SHORT_HASH],
            ),
        )
        for export, item in await note_exports(db, note_id)
    )


async def _attestations(db: AsyncSession, note_id: str) -> tuple[PacketAttestation, ...]:
    rows = await note_attestations(db, note_id)
    providers = {row.provider_id for row in rows}
    names = dict((await db.execute(select(Provider.id, Provider.name).where(Provider.id.in_(providers)))).all())
    return tuple(
        PacketAttestation(
            at=row.created_at,
            provider=names.get(row.provider_id, ""),
            purpose=row.purpose,
            answer=row.answer,
            wording=row.wording,
            shown=row.shown,
            comment=row.comment,
            ip=row.ip,
        )
        for row in rows
    )


async def _comments(db: AsyncSession, note_id: str) -> tuple[PacketComment, ...]:
    return tuple(
        PacketComment(
            at=comment.created_at,
            author=f"{comment.author_name} ({comment.author_role})",
            on=comment.finding_key or "Note",
            body=comment.body,
            removed=(removal.remover_name, removal.created_at) if removal else None,
        )
        for comment, removal in await note_comment_rows(db, note_id)
    )
