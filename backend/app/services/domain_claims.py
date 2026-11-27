from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.dns_txt import TxtResolver
from app.adapters.messenger import Messenger
from app.core.config import get_settings
from app.core.deps import Actor, Client
from app.core.errors import Conflict, Invalid, NotFound, Unauthorized
from app.core.security import digest, random_token
from app.models import PRACTICE_MEMBER_ROLES, DomainClaim, Practice, utcnow
from app.services.audit_log import SystemActor, record_activity, record_practice_access, record_system_access
from app.services.email_domains import ADMIN_MAILBOXES, claimable_domain
from app.services.rate_limits import DOMAIN_CHECKS_PER_CLAIM, DOMAIN_EMAILS_PER_CLAIM, DOMAIN_LINKS_PER_IP, hit

__all__ = [
    "ClaimScope",
    "DOMAIN_CLAIMED",
    "DOMAIN_VERIFIED",
    "JOIN_CHANGED",
    "TXT_PREFIX",
    "VerifiedDomain",
    "change_join",
    "claim_domain",
    "claims_in",
    "release_claim",
    "send_verification_email",
    "verify_by_dns",
    "verify_by_email",
]

TXT_PREFIX = "bodha-verify="
TOKEN_BYTES = 16
EMAIL_LINK_HOURS = 72
DOMAIN_CLAIMED = "domain claimed"
DOMAIN_VERIFIED = "domain verified"
DOMAIN_RELEASED = "domain released"
VERIFICATION_SENT = "domain verification sent"
JOIN_CHANGED = "domain join changed"
TAKEN = "this domain is already claimed"
NOT_FOUND = "domain claim not found"
NO_ADMIN_BY_DEFAULT = "people who join automatically cannot be admins"
LINK_EXPIRED = "this link has expired"
JOIN_OFF = "off"


@dataclass(frozen=True)
class ClaimScope:
    practice_id: str | None
    organization_id: str | None


@dataclass(frozen=True)
class VerifiedDomain:
    domain: str
    practice_name: str


async def claims_in(db: AsyncSession, scope: ClaimScope) -> list[dict[str, Any]]:
    rows = await db.execute(
        select(DomainClaim, Practice.name)
        .join(Practice, Practice.id == DomainClaim.practice_id)
        .where(*_in_scope(scope), DomainClaim.released_at.is_(None))
        .order_by(DomainClaim.domain, DomainClaim.created_at)
    )
    return [_claim_view(claim, practice_name) for claim, practice_name in rows.tuples()]


def _claim_view(claim: DomainClaim, practice_name: str) -> dict[str, Any]:
    return {
        "id": claim.id,
        "domain": claim.domain,
        "practice_id": claim.practice_id,
        "practice_name": practice_name,
        "verified": claim.verified_at is not None,
        "verified_at": claim.verified_at.isoformat() if claim.verified_at else None,
        "verified_via": claim.verified_via,
        "txt_record": None if claim.verified_at else f"{TXT_PREFIX}{claim.token}",
        "email_sent_to": None if claim.verified_at else claim.email_sent_to,
        "join_mode": claim.join_mode,
        "join_role": claim.join_role,
        "created_at": claim.created_at.isoformat(),
    }


def _in_scope(scope: ClaimScope) -> tuple[Any, ...]:
    if scope.organization_id is not None:
        return (DomainClaim.organization_id == scope.organization_id,)
    return DomainClaim.practice_id == scope.practice_id, DomainClaim.organization_id.is_(None)


async def claim_domain(db: AsyncSession, actor: Actor, scope: ClaimScope, practice: Practice, text: str) -> DomainClaim:
    domain = claimable_domain(text)
    if await _verified_holder(db, domain) is not None:
        raise Conflict(TAKEN)
    mine = await db.scalar(select(DomainClaim).where(*_in_scope(scope), *_live(), DomainClaim.domain == domain))
    if mine is not None:
        return mine
    claim = DomainClaim(
        domain=domain,
        practice_id=practice.id,
        organization_id=scope.organization_id,
        claimed_by=actor.user.id,
        token=secrets.token_hex(TOKEN_BYTES),
        join_mode=JOIN_OFF,
        join_role="viewer",
    )
    db.add(claim)
    await db.flush()
    _audit(db, actor, claim, practice, action=DOMAIN_CLAIMED, detail=claim.domain)
    await db.commit()
    return claim


def _live() -> tuple[Any, ...]:
    return (DomainClaim.released_at.is_(None),)


async def _verified_holder(db: AsyncSession, domain: str) -> DomainClaim | None:
    return await db.scalar(
        select(DomainClaim)
        .where(DomainClaim.domain == domain, DomainClaim.verified_at.is_not(None), *_live())
        .with_for_update()
    )


async def _owned(db: AsyncSession, scope: ClaimScope, claim_id: str) -> tuple[DomainClaim, Practice]:
    found = await db.execute(
        select(DomainClaim, Practice)
        .join(Practice, Practice.id == DomainClaim.practice_id)
        .where(DomainClaim.id == claim_id, *_in_scope(scope), *_live())
        .with_for_update(of=DomainClaim)
    )
    row = found.tuples().first()
    if row is None:
        raise NotFound(NOT_FOUND)
    return row


async def verify_by_dns(
    db: AsyncSession, resolver: TxtResolver, actor: Actor, scope: ClaimScope, claim_id: str
) -> None:
    await hit(db, DOMAIN_CHECKS_PER_CLAIM, claim_id)
    claim, practice = await _owned(db, scope, claim_id)
    if claim.verified_at is not None:
        return
    expected = f"{TXT_PREFIX}{claim.token}"
    records = await resolver.txt_records(claim.domain)
    if expected not in {record.strip() for record in records}:
        raise Conflict(f"add the TXT record {expected} to {claim.domain}, then check again")
    await _mark_verified(db, claim, "dns")
    _audit(db, actor, claim, practice, action=DOMAIN_VERIFIED, detail=f"{claim.domain} by DNS")
    await db.commit()


async def _mark_verified(db: AsyncSession, claim: DomainClaim, via: str) -> None:
    holder = await _verified_holder(db, claim.domain)
    if holder is not None and holder.id != claim.id:
        raise Conflict(TAKEN)
    claim.verified_at, claim.verified_via = utcnow(), via
    claim.email_token_hash, claim.email_expires_at = None, None


async def send_verification_email(
    db: AsyncSession, messenger: Messenger, actor: Actor, scope: ClaimScope, claim_id: str, *, mailbox: str
) -> None:
    if mailbox not in ADMIN_MAILBOXES:
        raise Invalid(f"choose one of {', '.join(ADMIN_MAILBOXES)}")
    await hit(db, DOMAIN_EMAILS_PER_CLAIM, claim_id)
    claim, practice = await _owned(db, scope, claim_id)
    if claim.verified_at is not None:
        raise Conflict("this domain is already verified")
    token = random_token()
    address = f"{mailbox}@{claim.domain}"
    claim.email_token_hash, claim.email_sent_to = digest(token), address
    claim.email_expires_at = utcnow() + timedelta(hours=EMAIL_LINK_HOURS)
    _audit(db, actor, claim, practice, action=VERIFICATION_SENT, detail=f"{claim.domain} to {mailbox}@")
    await db.commit()
    await messenger.email(
        address,
        subject=f"Confirm {claim.domain} for Bodha Assure",
        body=(
            f"{practice.name} asked to use {claim.domain} on Bodha Assure, so that colleagues with "
            f"{claim.domain} email addresses can join it. If you manage this domain and agree, confirm: "
            f"{get_settings().app_url}/verify-domain#{token}. If not, you can ignore this email."
        ),
    )


async def verify_by_email(db: AsyncSession, token: str, client: Client) -> VerifiedDomain:
    await hit(db, DOMAIN_LINKS_PER_IP, client.ip)
    found = await db.execute(
        select(DomainClaim, Practice)
        .join(Practice, Practice.id == DomainClaim.practice_id)
        .where(DomainClaim.email_token_hash == digest(token), *_live())
        .with_for_update(of=DomainClaim)
    )
    row = found.tuples().first()
    if row is None or row[0].email_expires_at is None or row[0].email_expires_at < utcnow():
        raise Unauthorized(LINK_EXPIRED)
    claim, practice = row
    mailbox = claim.email_sent_to or claim.domain
    await _mark_verified(db, claim, "email")
    detail = f"{claim.domain} by email to {mailbox}"
    record_system_access(db, SystemActor("domain-mailbox", mailbox[:120]), practice.id, DOMAIN_VERIFIED, detail=detail)
    record_activity(db, None, DOMAIN_VERIFIED, practice_id=practice.id, detail=detail)
    await db.commit()
    return VerifiedDomain(claim.domain, practice.name)


async def change_join(
    db: AsyncSession, actor: Actor, scope: ClaimScope, claim_id: str, *, mode: str, role: str
) -> None:
    claim, practice = await _owned(db, scope, claim_id)
    if claim.verified_at is None:
        raise Conflict("verify the domain first")
    if role not in PRACTICE_MEMBER_ROLES:
        raise Invalid("choose a role")
    if mode == "auto" and role == "admin":
        raise Invalid(NO_ADMIN_BY_DEFAULT)
    claim.join_mode, claim.join_role = mode, role
    _audit(db, actor, claim, practice, action=JOIN_CHANGED, detail=f"{claim.domain}: {mode}, {role}")
    await db.commit()


async def release_claim(db: AsyncSession, actor: Actor, scope: ClaimScope, claim_id: str) -> None:
    claim, practice = await _owned(db, scope, claim_id)
    claim.released_at, claim.released_by = utcnow(), actor.user.id
    _audit(db, actor, claim, practice, action=DOMAIN_RELEASED, detail=claim.domain)
    await db.commit()


def _audit(db: AsyncSession, actor: Actor, claim: DomainClaim, practice: Practice, *, action: str, detail: str) -> None:
    record_practice_access(db, practice.id, actor.user, action, detail=detail, client=actor.client)
    owner = "organization" if claim.organization_id else "practice"
    record_activity(db, actor, action, practice_id=practice.id, detail=f"{detail} ({owner} {practice.name})")
