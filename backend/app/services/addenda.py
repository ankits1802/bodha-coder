from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.core.config import get_settings
from app.core.deps import Actor, ProviderActor
from app.core.errors import Conflict, Invalid, NotFound, Unauthorized
from app.core.security import digest, issue_token, random_code, random_token, same_digest
from app.models import AddendumRequest, Note, NoteText, Practice, Provider, utcnow
from app.services.analysis import next_revision, request_analysis
from app.services.audit_log import record_access, record_provider_access
from app.services.placement import current_decisions, current_findings, refresh_placement
from app.services.review_actions import note_for
from app.services.routing import choices_for, open_questions

CODE_MINUTES = 10
MAX_CODE_ATTEMPTS = 5
OTHER_ANSWER = "Other"
DEFAULT_OPTIONS = ("Yes", "No", "Clinically undetermined")


@dataclass(frozen=True)
class QuestionEdit:
    key: str
    text: str


@dataclass(frozen=True)
class Answer:
    key: str
    choice: str
    comment: str | None


async def create_request(
    db: AsyncSession,
    messenger: Messenger,
    actor: Actor,
    note_id: str,
    *,
    edits: list[QuestionEdit],
    channel: str,
    hold: bool,
) -> AddendumRequest:
    note = await note_for(db, actor, note_id)
    provider = await db.get_one(Provider, note.provider_id)
    questions = await _chosen_questions(db, note, edits)
    destination = provider.email if channel == "email" else provider.phone
    if not destination:
        raise Invalid(f"{provider.name} has no {channel} on file")
    token = random_token()
    request = AddendumRequest(
        practice_id=note.practice_id,
        note_id=note.id,
        analysis_id=note.current_analysis_id,
        provider_id=provider.id,
        questions=questions,
        channel=channel,
        token_hash=digest(token),
        expires_at=utcnow() + timedelta(hours=get_settings().addendum_link_hours),
        hold_claim=hold,
        sent_by=actor.user.id,
        remind_at=utcnow() + timedelta(hours=12),
    )
    db.add(request)
    await db.flush()
    await refresh_placement(db, note)
    await _send_link(messenger, provider, channel, token, await db.get_one(Practice, note.practice_id))
    record_access(db, actor, "asked provider", note_id=note.id, detail=f"{len(edits)} questions by {channel}")
    await db.commit()
    return request


async def _chosen_questions(db: AsyncSession, note: Note, edits: list[QuestionEdit]) -> list[dict[str, Any]]:
    findings = await current_findings(db, note)
    choices = choices_for(findings, await current_decisions(db, note.id))
    open_items = {item.key: item for item in open_questions(findings, choices)}
    if not edits or any(edit.key not in open_items for edit in edits):
        raise Invalid("choose at least one open question")
    return [_question(open_items[edit.key], edit.text) for edit in edits]


def _question(finding: Any, text: str) -> dict[str, Any]:
    offered = finding.detail.get("options") or list(DEFAULT_OPTIONS)
    options = [option for option in offered if option != OTHER_ANSWER]
    return {
        "key": finding.key,
        "text": text.strip() or finding.title,
        "context": list(finding.evidence),
        "options": options + [OTHER_ANSWER],
    }


async def _send_link(messenger: Messenger, provider: Provider, channel: str, token: str, practice: Practice) -> None:
    link = f"{get_settings().app_url}/respond#{token}"
    body = f"{practice.name} has questions about one of your visit notes. Open securely: {link}"
    if channel == "email":
        await messenger.email(provider.email or "", subject=f"Questions from {practice.name}", body=body)
    else:
        await messenger.sms(provider.phone or "", body=body)


async def remind(db: AsyncSession, messenger: Messenger, actor: Actor, note_id: str) -> None:
    note = await note_for(db, actor, note_id)
    request = await db.scalar(
        select(AddendumRequest).where(AddendumRequest.note_id == note.id, AddendumRequest.status == "sent")
    )
    if request is None:
        raise NotFound("no open request for this note")
    token = random_token()
    request.token_hash, request.expires_at = (
        digest(token),
        utcnow() + timedelta(hours=get_settings().addendum_link_hours),
    )
    provider = await db.get_one(Provider, request.provider_id)
    await _send_link(messenger, provider, request.channel, token, await db.get_one(Practice, note.practice_id))
    await db.commit()


async def _open_request(db: AsyncSession, token: str) -> AddendumRequest:
    request = await db.scalar(select(AddendumRequest).where(AddendumRequest.token_hash == digest(token)))
    if request is None or request.status != "sent" or request.expires_at < utcnow():
        raise NotFound("this link is no longer valid")
    return request


async def send_code(db: AsyncSession, messenger: Messenger, token: str) -> str:
    request = await _open_request(db, token)
    provider = await db.get_one(Provider, request.provider_id)
    code = random_code()
    request.code_hash, request.code_expires_at, request.code_attempts = (
        digest(code),
        utcnow() + timedelta(minutes=CODE_MINUTES),
        0,
    )
    body = f"Your Bodha Coder verification code is {code}. It expires in {CODE_MINUTES} minutes."
    if request.channel == "email":
        await messenger.email(provider.email or "", subject="Your verification code", body=body)
    else:
        await messenger.sms(provider.phone or "", body=body)
    await db.commit()
    return _masked(provider.email if request.channel == "email" else provider.phone)


def _masked(destination: str | None) -> str:
    value = destination or ""
    return value[:2] + "•" * max(len(value) - 4, 3) + value[-2:]


async def verify_code(db: AsyncSession, token: str, code: str) -> str:
    request = await _open_request(db, token)
    if (
        request.code_attempts >= MAX_CODE_ATTEMPTS
        or request.code_expires_at is None
        or request.code_expires_at < utcnow()
    ):
        raise Unauthorized("ask for a new code")
    request.code_attempts += 1
    if not same_digest(code.strip(), request.code_hash):
        await db.commit()
        raise Unauthorized("that code is not correct")
    request.code_hash = None
    await db.commit()
    return issue_token(
        "provider",
        request.provider_id,
        get_settings().provider_session_minutes,
        req=request.id,
        prc=request.practice_id,
    )


async def provider_request(
    db: AsyncSession, actor: ProviderActor
) -> tuple[AddendumRequest, Note, Provider, list[NoteText]]:
    request, note, provider = await _load_for_provider(db, actor)
    texts = list(
        (await db.scalars(select(NoteText).where(NoteText.note_id == note.id).order_by(NoteText.revision))).all()
    )
    record_provider_access(db, actor, provider.name, "opened addendum request", note_id=note.id)
    await db.commit()
    return request, note, provider, texts


async def provider_document_key(db: AsyncSession, actor: ProviderActor) -> str:
    _, note, provider = await _load_for_provider(db, actor)
    record_provider_access(db, actor, provider.name, "opened PDF", note_id=note.id)
    await db.commit()
    return note.file_key


async def _load_for_provider(db: AsyncSession, actor: ProviderActor) -> tuple[AddendumRequest, Note, Provider]:
    request = await db.get(AddendumRequest, actor.request_id)
    if request is None or request.provider_id != actor.provider_id or request.practice_id != actor.practice_id:
        raise NotFound("request not found")
    return request, await db.get_one(Note, request.note_id), await db.get_one(Provider, request.provider_id)


async def answer(db: AsyncSession, actor: ProviderActor, answers: list[Answer], *, confirmed: bool) -> AddendumRequest:
    request, note, provider = await _load_for_provider(db, actor)
    if request.status != "sent":
        raise Conflict("this request was already answered")
    if not confirmed:
        raise Invalid("confirm the answers are clinically accurate")
    chosen = _validated(request.questions, answers)
    text = addendum_text(provider.name, request.questions, chosen)
    request.answers = [{"key": item.key, "choice": item.choice, "comment": item.comment} for item in chosen]
    request.addendum_text, request.status, request.answered_at = text, "answered", utcnow()
    db.add(
        NoteText(
            note_id=note.id,
            revision=await next_revision(db, NoteText, note.id),
            source="addendum",
            text=text,
            addendum_request_id=request.id,
        )
    )
    note.status = "queued"
    await request_analysis(db, note, reason="addendum")
    record_provider_access(db, actor, provider.name, "signed addendum", note_id=note.id)
    await db.commit()
    return request


def _validated(questions: list[dict[str, Any]], answers: list[Answer]) -> list[Answer]:
    by_key = {item.key: item for item in answers}
    chosen: list[Answer] = []
    for question in questions:
        found = by_key.get(question["key"])
        if found is None or found.choice not in question["options"]:
            raise Invalid("answer every question with one of its choices")
        if found.choice == OTHER_ANSWER and not (found.comment or "").strip():
            raise Invalid("write your answer when choosing Other")
        chosen.append(found)
    return chosen


def addendum_text(provider_name: str, questions: list[dict[str, Any]], answers: list[Answer]) -> str:
    stamp = utcnow().strftime("%d %b %Y")
    lines = [f"Addendum by {provider_name}, {stamp}."]
    for question, item in zip(questions, answers, strict=True):
        reply = (item.comment or "").strip() if item.choice == OTHER_ANSWER else item.choice
        extra = f" {item.comment.strip()}" if item.comment and item.choice != OTHER_ANSWER else ""
        lines.append(f"{question['text']} {reply}.{extra}")
    return "\n".join(lines)
