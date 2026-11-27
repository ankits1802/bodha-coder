from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.message_errors import MessageNotSent
from app.adapters.messenger import Messenger
from app.adapters.seal_keys import RecordSigner
from app.codes.billing_codes import Code
from app.codes.em import is_em_code
from app.core.config import get_settings
from app.core.deps import Actor, ProviderActor
from app.core.errors import Conflict, Invalid
from app.core.security import digest, random_token
from app.models import LEVEL_CHANGE_PURPOSE, AddendumRequest, ApprovedClaim, Note, Practice, Provider, User, utcnow
from app.services.addenda import load_for_provider, send_link
from app.services.attestations import LEVEL_ATTESTATION, Statement, checked_wording, record_attestation
from app.services.audit_log import record_access, record_provider_access
from app.services.claim_snapshots import snapshot_codes
from app.services.finding import Finding
from app.services.inbox import Notice, notify
from app.services.placement import refresh_placement
from app.services.provider_channels import require_channel, usable_channel
from app.services.sealing import provider_signer, seal_attestation
from app.services.signatures import SignatureChoice, provider_signature

__all__ = [
    "LEVEL_ANSWERS",
    "LEVEL_KEY",
    "LevelAnswer",
    "answer_level_change",
    "ask_level_confirmation",
    "level_change",
    "level_text",
    "level_view",
    "shown_text",
]

logger = logging.getLogger("bodha.levels")
LEVEL_KEY = "level_change"
LEVEL_ANSWERS = {"confirm": "Confirm", "disagree": "Disagree"}
NO_LEVEL = "none"
REMIND_AFTER = timedelta(hours=12)
ACTIONS = {"confirm": "confirmed visit level", "disagree": "disagreed with visit level"}
DISAGREED = "level_disagreed"


@dataclass(frozen=True)
class LevelAnswer:
    answer: str
    comment: str | None
    confirmed: bool
    attestation: str | None
    signature: SignatureChoice


def level_change(billed: Sequence[Code], approved: Sequence[Code]) -> tuple[str | None, str | None] | None:
    before, after = _visit_code(billed), _visit_code(approved)
    return None if before == after else (before, after)


def level_text(billed: str | None, approved: str | None, service_date: date) -> str:
    return (
        f"Visit of {service_date.strftime('%d %b %Y')}\n"
        f"Billed level: {billed or NO_LEVEL}\n"
        f"Approved level: {approved or NO_LEVEL}"
    )


def shown_text(request: AddendumRequest) -> str:
    question = request.questions[0]
    quotes = [f"“{quote}”" for quote in question.get("context") or []]
    return "\n".join([question["text"], *(["Evidence from the note:", *quotes] if quotes else [])])


async def level_view(db: AsyncSession, request: AddendumRequest) -> dict[str, str | None] | None:
    if request.purpose != LEVEL_CHANGE_PURPOSE or request.approved_claim_id is None:
        return None
    snapshot = await db.get_one(ApprovedClaim, request.approved_claim_id)
    billed = [Code.from_json(item) for item in snapshot.content.get("billed", [])]
    before, after = level_change(billed, snapshot_codes(snapshot)) or (None, None)
    return {"billed": before, "approved": after, "shown": shown_text(request)}


async def ask_level_confirmation(
    db: AsyncSession,
    messenger: Messenger,
    actor: Actor,
    note: Note,
    *,
    snapshot: ApprovedClaim,
    findings: list[Finding],
) -> AddendumRequest | None:
    practice = actor.own_practice
    billed = [Code.from_json(item) for item in snapshot.content.get("billed", [])]
    change = level_change(billed, snapshot_codes(snapshot))
    if not practice.confirm_level_changes or change is None:
        return None
    provider = await db.get_one(Provider, note.provider_id)
    channel = usable_channel(provider.channel, name=provider.name, email=provider.email)
    require_channel(provider, channel)
    token = random_token()
    request = _level_request(note, practice, provider, snapshot=snapshot, findings=findings, change=change)
    request.channel, request.token_hash, request.sent_by = channel, digest(token), actor.user.id
    db.add(request)
    await db.flush()
    await send_link(messenger, provider, channel, token, practice, purpose=LEVEL_CHANGE_PURPOSE)
    before, after = change
    detail = f"{before or NO_LEVEL} to {after or NO_LEVEL}"
    record_access(db, actor, "asked provider to confirm level", note_id=note.id, detail=detail)
    return request


def _level_request(
    note: Note,
    practice: Practice,
    provider: Provider,
    *,
    snapshot: ApprovedClaim,
    findings: list[Finding],
    change: tuple[str | None, str | None],
) -> AddendumRequest:
    em = next((item for item in findings if item.kind == "em"), None)
    question = {
        "key": LEVEL_KEY,
        "text": level_text(change[0], change[1], note.service_date),
        "context": list(em.evidence) if em else [],
        "options": list(LEVEL_ANSWERS.values()),
    }
    return AddendumRequest(
        practice_id=note.practice_id,
        note_id=note.id,
        analysis_id=note.current_analysis_id,
        provider_id=provider.id,
        questions=[question],
        expires_at=utcnow() + timedelta(hours=get_settings().addendum_link_hours),
        hold_claim=practice.hold_until_confirmed,
        remind_at=utcnow() + REMIND_AFTER,
        purpose=LEVEL_CHANGE_PURPOSE,
        approved_claim_id=snapshot.id,
    )


async def answer_level_change(
    db: AsyncSession, messenger: Messenger, signer: RecordSigner, actor: ProviderActor, reply: LevelAnswer
) -> AddendumRequest:
    request, note, provider = await load_for_provider(db, actor)
    if request.purpose != LEVEL_CHANGE_PURPOSE:
        raise Conflict("answer the questions with the addendum form instead")
    if request.status != "sent":
        raise Conflict("this request was already answered")
    comment = _checked_reply(reply)
    wording = checked_wording(LEVEL_ATTESTATION, reply.attestation)
    signature = await provider_signature(db, actor, reply.signature)
    request.answers = [{"key": LEVEL_KEY, "choice": LEVEL_ANSWERS[reply.answer], "comment": comment}]
    request.status, request.answered_at, request.remind_at = "answered", utcnow(), None
    statement = Statement(wording, shown_text(request), reply.answer, comment)
    attestation = await record_attestation(db, actor, request, statement)
    await seal_attestation(db, signer, provider_signer(actor, provider, signature), attestation, note)
    record_provider_access(db, actor, provider.name, ACTIONS[reply.answer], note_id=note.id)
    if reply.answer == "disagree":
        await _reopen_for_review(db, actor, note, provider)
        await _notify_approver(db, messenger, note, request, provider)
    await db.commit()
    return request


def _checked_reply(reply: LevelAnswer) -> str | None:
    if reply.answer not in LEVEL_ANSWERS:
        raise Invalid("answer confirm or disagree")
    if not reply.confirmed:
        raise Invalid("confirm you reviewed the levels and the evidence")
    comment = (reply.comment or "").strip() or None
    if reply.answer == "disagree" and comment is None:
        raise Invalid("say why you disagree")
    return comment


async def _reopen_for_review(db: AsyncSession, actor: ProviderActor, note: Note, provider: Provider) -> None:
    if note.status != "approved":
        return
    note.status, note.approved_by, note.approved_at = "ready", None, None
    await refresh_placement(db, note)
    record_provider_access(db, actor, provider.name, "reopened after disagreement", note_id=note.id)


async def _notify_approver(
    db: AsyncSession, messenger: Messenger, note: Note, request: AddendumRequest, provider: Provider
) -> None:
    snapshot = await db.get(ApprovedClaim, request.approved_claim_id) if request.approved_claim_id else None
    approver = await db.get(User, snapshot.approved_by) if snapshot and snapshot.approved_by else None
    if approver is None or approver.status != "active":
        return
    await notify(db, note.practice_id, [approver.id], Notice(DISAGREED, provider.name, note_id=note.id))
    practice = await db.get_one(Practice, note.practice_id)
    link = f"{get_settings().app_url}/notes/{note.id}?tab=history"
    body = f"{practice.name}: a provider disagreed with a visit level you approved. Open: {link}"
    try:
        await messenger.email(approver.email, subject=f"Visit level disagreement at {practice.name}", body=body)
    except MessageNotSent:
        logger.warning("approver of note %s was not told of a level disagreement", note.id)


def _visit_code(codes: Sequence[Code]) -> str | None:
    return next((code.code for code in codes if code.type == "CPT" and is_em_code(code.code)), None)
