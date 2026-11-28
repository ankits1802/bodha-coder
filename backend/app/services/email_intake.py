from __future__ import annotations

import logging
from collections.abc import Collection, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_listing import ListingStore
from app.core.calendar import zone_named
from app.core.config import get_settings
from app.core.db import try_advisory_lock
from app.core.security import same_digest
from app.models import SENDER_LENGTH, IntakeAddress, IntakeMessage, IntakeSender, IntakeTest, Practice, utcnow
from app.services.email_intake_files import ACCEPTED, FileOutcome, deliver_attachments
from app.services.intake import accepts_intake
from app.services.intake_mail import (
    INBOUND_PREFIX,
    MESSAGE_TYPE,
    Envelope,
    Mail,
    envelope_message_id,
    local_part_at,
    probe_reference,
    read_envelope,
    read_mail,
    sender_allowed,
)

__all__ = ["EMAIL_INTAKE_LOCK", "MAX_MESSAGE_FILES", "Gate", "poll_email_intake", "refusal_of"]

logger = logging.getLogger("bodha.intake")
EMAIL_INTAKE_LOCK = "email intake"
MAX_MESSAGE_FILES = 50
SCANS = ("spam", "virus")
AUTHENTICATION = "dmarc"


@dataclass(frozen=True)
class Gate:
    current: bool
    practice_open: bool
    allowed_senders: Collection[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class Stores:
    inbound: ListingStore
    documents: ListingStore


@dataclass(frozen=True)
class Delivery:
    envelope: Envelope
    mail: Mail
    address: IntakeAddress | None
    now: datetime


async def poll_email_intake(
    db: AsyncSession, store: ListingStore, now: datetime, *, inbound: ListingStore | None = None
) -> int:
    if now.tzinfo is None:
        raise ValueError("now needs a time zone")
    domain = get_settings().email_intake_domain
    if not domain:
        return 0
    async with try_advisory_lock(db, EMAIL_INTAKE_LOCK) as held:
        return await _poll(db, Stores(inbound or store, store), domain, now) if held else 0


def refusal_of(envelope: Envelope, mail: Mail, gate: Gate) -> str | None:
    if not gate.current:
        return "retired_address"
    if not gate.practice_open:
        return "practice_closed"
    if not envelope.passed(*SCANS):
        return "failed_scan"
    if not envelope.passed(AUTHENTICATION):
        return "not_authenticated"
    if not sender_allowed(mail.sender, gate.allowed_senders):
        return "sender_not_allowed"
    if not any(attachment.is_pdf for attachment in mail.attachments):
        return "no_pdf"
    if len(mail.attachments) > MAX_MESSAGE_FILES:
        return "too_many_files"
    return None


async def _poll(db: AsyncSession, stores: Stores, domain: str, now: datetime) -> int:
    handled = 0
    for key in await stores.inbound.list_keys(INBOUND_PREFIX):
        message_id = envelope_message_id(key)
        if message_id is None:
            continue
        try:
            await _handle(db, stores, key, domain, now)
        except Exception:
            await db.rollback()
            logger.exception("email intake message %s failed", message_id)
            continue
        handled += 1
    return handled


async def _handle(db: AsyncSession, stores: Stores, key: str, domain: str, now: datetime) -> None:
    envelope = read_envelope(await stores.inbound.get(key))
    if envelope.envelope_key != key:
        raise ValueError("an intake envelope names another message than its key")
    raw = await stores.inbound.get(envelope.raw_key)
    await stores.documents.put(envelope.retained_key, raw, content_type=MESSAGE_TYPE)
    mail = read_mail(raw)
    for address in await _addresses(db, envelope, domain):
        await _record_once(db, stores.documents, Delivery(envelope, mail, address, now))
    await stores.inbound.delete([key, envelope.raw_key])


async def _addresses(db: AsyncSession, envelope: Envelope, domain: str) -> Sequence[IntakeAddress | None]:
    local_parts = {part for recipient in envelope.recipients if (part := local_part_at(recipient, domain))}
    if not local_parts:
        return [None]
    query = select(IntakeAddress).where(IntakeAddress.local_part.in_(local_parts)).order_by(IntakeAddress.created_at)
    found = list((await db.scalars(query)).all())
    return found or [None]


async def _record_once(db: AsyncSession, store: ListingStore, delivery: Delivery) -> None:
    address_id = delivery.address.id if delivery.address else None
    recorded = await db.scalar(
        select(IntakeMessage.id).where(
            IntakeMessage.message_key == delivery.envelope.message_id,
            IntakeMessage.address_id.is_not_distinct_from(address_id),
        )
    )
    if recorded is not None:
        return
    if delivery.address is None:
        db.add(_message(delivery, None, "refused", "unknown_address"))
    else:
        await _deliver(db, store, delivery, delivery.address)
    await db.commit()


async def _deliver(db: AsyncSession, store: ListingStore, delivery: Delivery, address: IntakeAddress) -> None:
    probe = await _probe(db, address, delivery.mail)
    if probe is not None:
        record = _message(delivery, address.practice_id, "test", None)
        db.add(record)
        await db.flush()
        probe.arrived_at, probe.message_id = utcnow(), record.id
        return
    practice = await db.get_one(Practice, address.practice_id)
    gate = Gate(address.retired_at is None, accepts_intake(practice, delivery.now), await _allowed(db, practice.id))
    refusal = refusal_of(delivery.envelope, delivery.mail, gate)
    if refusal is not None:
        db.add(_message(delivery, practice.id, "refused", refusal))
        return
    today = delivery.now.astimezone(zone_named(practice.time_zone)).date()
    files = await deliver_attachments(db, store, practice, delivery.mail.attachments, today=today)
    accepted = any(file.outcome == ACCEPTED for file in files)
    record = _message(
        delivery, practice.id, "accepted" if accepted else "refused", None if accepted else "files_refused"
    )
    db.add(_with_files(record, files))


async def _probe(db: AsyncSession, address: IntakeAddress, mail: Mail) -> IntakeTest | None:
    reference = probe_reference(mail.subject)
    if reference is None:
        return None
    probe = await db.get(IntakeTest, reference.test_id, with_for_update=True)
    if probe is None or probe.address_id != address.id or probe.arrived_at is not None:
        return None
    return probe if same_digest(reference.token, probe.token_hash) else None


async def _allowed(db: AsyncSession, practice_id: str) -> frozenset[str]:
    query = select(IntakeSender.pattern).where(
        IntakeSender.practice_id == practice_id, IntakeSender.removed_at.is_(None)
    )
    return frozenset((await db.scalars(query)).all())


def _message(delivery: Delivery, practice_id: str | None, outcome: str, reason: str | None) -> IntakeMessage:
    sender = delivery.mail.sender if practice_id else None
    return IntakeMessage(
        message_key=delivery.envelope.message_id,
        practice_id=practice_id,
        address_id=delivery.address.id if delivery.address else None,
        received_at=delivery.envelope.received_at,
        sender=sender[:SENDER_LENGTH] if sender else None,
        outcome=outcome,
        reason=reason,
        accepted_files=0,
        refused_files=0,
        files=[],
        verdicts=dict(delivery.envelope.verdicts),
    )


def _with_files(record: IntakeMessage, files: Sequence[FileOutcome]) -> IntakeMessage:
    record.files = [file.as_json() for file in files]
    record.accepted_files = sum(file.outcome == ACCEPTED for file in files)
    record.refused_files = len(files) - record.accepted_files
    return record
