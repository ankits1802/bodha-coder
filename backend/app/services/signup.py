from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.adapters.oidc import ProviderIdentity
from app.adapters.oidc_providers import PROVIDERS, provider_label
from app.core.calendar import today_in, zone_named
from app.core.config import Settings, get_settings
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid, NotFound, Unauthorized
from app.core.security import TokenError, issue_token, read_token
from app.models import utcnow
from app.services.audit_log import record_activity
from app.services.auth import MfaChallenge, Tokens, sign_in_user
from app.services.identity_sign_in import bind_identity
from app.services.practice_accounts import (
    AdminDraft,
    NewPractice,
    PracticeDraft,
    add_practice_with_admin,
    email_in_use,
    normal_email,
)
from app.services.rate_limits import SIGNUP_PER_EMAIL, SIGNUP_PER_IP, hit
from app.services.team import send_invite

SIGNUP_TOKEN = "signup"
SIGNUP_MINUTES = 30
EMAIL_METHOD = "email"
SELF_SOURCE = "self"
TRIAL = "trial"
SIGNED_UP = "practice signed up"
NOT_AVAILABLE = "Self sign-up is not available"
START_AGAIN = "start sign-up again"


@dataclass(frozen=True)
class EmailSignup:
    name: str
    practice_name: str
    email: str
    time_zone: str
    agreed: bool


@dataclass(frozen=True)
class IdentitySignup:
    name: str
    practice_name: str
    time_zone: str
    agreed: bool


@dataclass(frozen=True)
class Visitor:
    ip: str | None
    agent: str | None


def signup_options(settings: Settings) -> dict[str, Any]:
    return {
        "enabled": settings.self_signup_enabled,
        "terms_url": settings.terms_url,
        "baa_url": settings.baa_url,
        "privacy_url": settings.privacy_url,
        "test_data_only": not settings.baa_url,
    }


def ensure_signup_open() -> None:
    if not get_settings().self_signup_enabled:
        raise NotFound(NOT_AVAILABLE)


async def check_email_signup(db: AsyncSession, form: EmailSignup, *, ip: str | None) -> None:
    ensure_signup_open()
    _require_agreement(form.agreed)
    zone_named(form.time_zone)
    await hit(db, SIGNUP_PER_IP, ip)
    await hit(db, SIGNUP_PER_EMAIL, normal_email(form.email))


async def request_email_signup(
    db: AsyncSession, messenger: Messenger, form: EmailSignup, *, ip: str | None, agent: str | None
) -> None:
    if await email_in_use(db, form.email):
        await _send_existing_account(messenger, normal_email(form.email))
        return
    created = await _trial_practice(
        db, form.practice_name, form.time_zone, AdminDraft(form.name, form.email, "invited")
    )
    created.practice.signup = _signup_record(created, EMAIL_METHOD, ip)
    await send_invite(db, messenger, created.admin, practice_name=created.practice.name)
    _record_signup(db, created, EMAIL_METHOD, Visitor(ip, agent))
    await db.commit()


def identity_token(identity: ProviderIdentity) -> str:
    claims = {"idp": identity.provider, "email": identity.email, "name": identity.name}
    return issue_token(SIGNUP_TOKEN, identity.subject, SIGNUP_MINUTES, **claims)


def pending_identity(token: str | None) -> ProviderIdentity:
    ensure_signup_open()
    if not token:
        raise Unauthorized(START_AGAIN)
    try:
        claims = read_token(token, SIGNUP_TOKEN)
    except TokenError as error:
        raise Unauthorized(START_AGAIN) from error
    provider = str(claims.get("idp"))
    if provider not in PROVIDERS:
        raise Unauthorized(START_AGAIN)
    return ProviderIdentity(provider, str(claims["sub"]), str(claims["email"]), str(claims.get("name") or ""))


async def complete_identity_signup(
    db: AsyncSession, token: str | None, form: IdentitySignup, visitor: Visitor
) -> Tokens | MfaChallenge:
    identity = pending_identity(token)
    _require_agreement(form.agreed)
    zone_named(form.time_zone)
    await hit(db, SIGNUP_PER_IP, visitor.ip)
    if await email_in_use(db, identity.email):
        raise Conflict("this email already has an account; sign in instead")
    admin = AdminDraft(form.name, identity.email, "active")
    created = await _trial_practice(db, form.practice_name, form.time_zone, admin)
    await bind_identity(db, created.admin, identity.provider, identity.subject)
    created.practice.signup = _signup_record(created, identity.provider, visitor.ip)
    _record_signup(db, created, identity.provider, visitor)
    await db.commit()
    label = provider_label(identity.provider)
    return await sign_in_user(db, created.admin, method=label, ip=visitor.ip, agent=visitor.agent)


def _require_agreement(agreed: bool) -> None:
    if agreed is not True:
        raise Invalid("agree to the terms to start a trial")


async def _trial_practice(db: AsyncSession, name: str, time_zone: str, admin: AdminDraft) -> NewPractice:
    settings = get_settings()
    zone = zone_named(time_zone)
    ends = today_in(zone) + timedelta(days=settings.trial_days)
    draft = PracticeDraft(name, TRIAL, TRIAL, settings.trial_seats, zone.key, renews_on=ends)
    return await add_practice_with_admin(db, draft, admin)


def _signup_record(created: NewPractice, method: str, ip: str | None) -> dict[str, Any]:
    return {
        "source": SELF_SOURCE,
        "agreement_version": get_settings().agreement_version,
        "accepted_at": utcnow().isoformat(),
        "accepted_by": created.admin.id,
        "method": method,
        "ip": ip,
    }


def _record_signup(db: AsyncSession, created: NewPractice, method: str, visitor: Visitor) -> None:
    actor = Actor(created.admin, created.practice, visitor.ip, visitor.agent)
    detail = f"{created.practice.name}, {method}"
    record_activity(db, actor, SIGNED_UP, practice_id=created.practice.id, detail=detail)


async def _send_existing_account(messenger: Messenger, email: str) -> None:
    app_url = get_settings().app_url
    await messenger.email(
        email,
        subject="You already have a Bodha Coder account",
        body=(
            "Someone asked to start a Bodha Coder trial with this email, which already has an account. "
            f"Sign in: {app_url}/sign-in. Forgot your password? Reset it: {app_url}/forgot-password. "
            "If this was not you, you can ignore this email."
        ),
    )
