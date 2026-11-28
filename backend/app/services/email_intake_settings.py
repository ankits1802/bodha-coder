from __future__ import annotations

import base64
import secrets
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.message_errors import MessageNotSent
from app.adapters.messenger import Messenger
from app.core.config import get_settings
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid, NotFound, Unavailable
from app.core.security import digest
from app.models import IntakeAddress, IntakeMessage, IntakeSender, IntakeTest, Practice, utcnow
from app.services.audit_log import record_activity
from app.services.intake_mail import ProbeReference, probe_subject, sender_pattern
from app.services.rate_limits import INTAKE_TESTS_PER_PRACTICE, hit

__all__ = [
    "ADDRESS_ISSUED",
    "ADDRESS_RETIRED",
    "MAX_SENDERS",
    "MESSAGE_PAGE",
    "SENDER_ADDED",
    "SENDER_REMOVED",
    "TEST_SENT",
    "add_sender",
    "email_intake_view",
    "intake_test_view",
    "issue_address",
    "message_page",
    "new_local_part",
    "remove_sender",
    "retire_address",
    "send_test",
]

ADDRESS_ISSUED = "email intake address issued"
ADDRESS_RETIRED = "email intake address retired"
SENDER_ADDED = "email intake sender added"
SENDER_REMOVED = "email intake sender removed"
TEST_SENT = "email intake test sent"
MAX_SENDERS = 100
MESSAGE_PAGE = 50
PREVIOUS_SHOWN = 20
LOCAL_PART_BYTES = 10
NOT_SET_UP = "email intake is not set up for Bodha yet"
TEST_BODY = "Bodha sent this message to check that mail sent to this address arrives. Nothing needs to be done."


def new_local_part() -> str:
    return base64.b32encode(secrets.token_bytes(LOCAL_PART_BYTES)).decode("ascii").lower()


async def email_intake_view(db: AsyncSession, actor: Actor) -> dict[str, Any]:
    domain = get_settings().email_intake_domain
    addresses = (
        await db.scalars(
            select(IntakeAddress)
            .where(IntakeAddress.practice_id == actor.practice_id)
            .order_by(IntakeAddress.created_at.desc(), IntakeAddress.id)
            .limit(PREVIOUS_SHOWN + 1)
        )
    ).all()
    current = next((address for address in addresses if address.retired_at is None), None)
    senders = await _current_senders(db, actor.practice_id)
    return {
        "available": bool(domain),
        "address": _address(current, domain) if current and domain else None,
        "address_since": current.created_at.isoformat() if current else None,
        "previous": [_previous(address, domain) for address in addresses if address.retired_at is not None],
        "senders": [_sender_view(sender) for sender in senders],
    }


async def issue_address(db: AsyncSession, actor: Actor) -> dict[str, Any]:
    if not get_settings().email_intake_domain:
        raise Conflict(NOT_SET_UP)
    await db.get_one(Practice, actor.practice_id, with_for_update=True, populate_existing=True)
    replaced = await _retire_current(db, actor)
    db.add(IntakeAddress(practice_id=actor.practice_id, local_part=new_local_part(), created_by=actor.user.id))
    detail = "new address, the previous one retired" if replaced else "first address"
    record_activity(db, actor, ADDRESS_ISSUED, practice_id=actor.practice_id, detail=detail)
    await db.commit()
    return await email_intake_view(db, actor)


async def retire_address(db: AsyncSession, actor: Actor) -> dict[str, Any]:
    await db.get_one(Practice, actor.practice_id, with_for_update=True, populate_existing=True)
    if not await _retire_current(db, actor):
        raise NotFound("this practice has no email intake address")
    record_activity(db, actor, ADDRESS_RETIRED, practice_id=actor.practice_id, detail="email intake off")
    await db.commit()
    return await email_intake_view(db, actor)


async def add_sender(db: AsyncSession, actor: Actor, text: str) -> dict[str, Any]:
    pattern, kind = sender_pattern(text)
    await db.get_one(Practice, actor.practice_id, with_for_update=True, populate_existing=True)
    senders = await _current_senders(db, actor.practice_id)
    if any(sender.pattern == pattern for sender in senders):
        raise Conflict(f"{pattern} is already allowed")
    if len(senders) >= MAX_SENDERS:
        raise Invalid(f"allow at most {MAX_SENDERS} senders")
    db.add(IntakeSender(practice_id=actor.practice_id, pattern=pattern, kind=kind, added_by=actor.user.id))
    record_activity(db, actor, SENDER_ADDED, practice_id=actor.practice_id, detail=pattern)
    await db.commit()
    return await email_intake_view(db, actor)


async def remove_sender(db: AsyncSession, actor: Actor, sender_id: str) -> dict[str, Any]:
    sender = await db.scalar(
        select(IntakeSender)
        .where(
            IntakeSender.id == sender_id,
            IntakeSender.practice_id == actor.practice_id,
            IntakeSender.removed_at.is_(None),
        )
        .with_for_update()
    )
    if sender is None:
        raise NotFound("sender not found")
    sender.removed_at, sender.removed_by = utcnow(), actor.user.id
    record_activity(db, actor, SENDER_REMOVED, practice_id=actor.practice_id, detail=sender.pattern)
    await db.commit()
    return await email_intake_view(db, actor)


async def send_test(db: AsyncSession, messenger: Messenger, actor: Actor) -> dict[str, Any]:
    domain = get_settings().email_intake_domain
    if not domain:
        raise Conflict(NOT_SET_UP)
    current = await _current_address(db, actor.practice_id)
    if current is None:
        raise Conflict("get an email intake address first")
    await hit(db, INTAKE_TESTS_PER_PRACTICE, actor.practice_id)
    token = secrets.token_hex(16)
    probe = IntakeTest(
        practice_id=actor.practice_id, address_id=current.id, token_hash=digest(token), requested_by=actor.user.id
    )
    db.add(probe)
    await db.flush()
    try:
        await messenger.email(
            _address(current, domain), subject=probe_subject(ProbeReference(probe.id, token)), body=TEST_BODY
        )
    except MessageNotSent as error:
        await db.rollback()
        raise Unavailable("the test message could not be sent; try again") from error
    record_activity(db, actor, TEST_SENT, practice_id=actor.practice_id, detail=probe.id)
    await db.commit()
    return _test_view(probe)


async def intake_test_view(db: AsyncSession, actor: Actor, test_id: str) -> dict[str, Any]:
    probe = await db.get(IntakeTest, test_id)
    if probe is None or probe.practice_id != actor.practice_id:
        raise NotFound("test not found")
    return _test_view(probe)


async def message_page(db: AsyncSession, actor: Actor, *, offset: int) -> dict[str, Any]:
    mine = IntakeMessage.practice_id == actor.practice_id
    rows = (
        await db.scalars(
            select(IntakeMessage)
            .where(mine)
            .order_by(IntakeMessage.created_at.desc(), IntakeMessage.id)
            .offset(offset)
            .limit(MESSAGE_PAGE)
        )
    ).all()
    total = await db.scalar(select(func.count()).select_from(IntakeMessage).where(mine)) or 0
    return {"items": [_message_view(row) for row in rows], "total": total, "offset": offset, "page_size": MESSAGE_PAGE}


async def _current_address(db: AsyncSession, practice_id: str) -> IntakeAddress | None:
    return await db.scalar(
        select(IntakeAddress).where(IntakeAddress.practice_id == practice_id, IntakeAddress.retired_at.is_(None))
    )


async def _retire_current(db: AsyncSession, actor: Actor) -> bool:
    current = await _current_address(db, actor.practice_id)
    if current is None:
        return False
    current.retired_at, current.retired_by = utcnow(), actor.user.id
    await db.flush()
    return True


async def _current_senders(db: AsyncSession, practice_id: str) -> list[IntakeSender]:
    query = (
        select(IntakeSender)
        .where(IntakeSender.practice_id == practice_id, IntakeSender.removed_at.is_(None))
        .order_by(IntakeSender.pattern)
    )
    return list((await db.scalars(query)).all())


def _address(address: IntakeAddress, domain: str) -> str:
    return f"{address.local_part}@{domain}"


def _previous(address: IntakeAddress, domain: str) -> dict[str, Any]:
    retired = address.retired_at.isoformat() if address.retired_at else None
    shown = _address(address, domain) if domain else None
    return {"address": shown, "since": address.created_at.isoformat(), "until": retired}


def _sender_view(sender: IntakeSender) -> dict[str, Any]:
    return {"id": sender.id, "pattern": sender.pattern, "kind": sender.kind, "added_at": sender.created_at.isoformat()}


def _test_view(probe: IntakeTest) -> dict[str, Any]:
    arrived = probe.arrived_at.isoformat() if probe.arrived_at else None
    return {"id": probe.id, "sent_at": probe.created_at.isoformat(), "arrived_at": arrived}


def _message_view(row: IntakeMessage) -> dict[str, Any]:
    return {
        "id": row.id,
        "received_at": row.received_at.isoformat(),
        "sender": row.sender,
        "outcome": row.outcome,
        "reason": row.reason,
        "accepted_files": row.accepted_files,
        "refused_files": row.refused_files,
        "files": [
            {"outcome": file["outcome"], "reason": file.get("reason"), "note_id": file.get("note_id")}
            for file in row.files
        ],
    }
