from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.adapters.oidc import ProviderIdentity
from app.adapters.oidc_providers import PROVIDERS, provider_label
from app.adapters.seal_keys import RecordSigner
from app.core.calendar import today_in, zone_named
from app.core.config import Settings, get_settings
from app.core.deps import Actor, Client
from app.core.errors import Conflict, Forbidden, Invalid, NotFound, Unauthorized
from app.core.realms import Site
from app.core.security import TokenError, issue_token, read_token
from app.models import PRACTICE_REALM, User, utcnow
from app.services.account_lookup import account_by_email, email_in_use, normal_email
from app.services.audit_log import record_activity
from app.services.auth import MfaChallenge, Tokens, sign_in_user
from app.services.identity_sign_in import admit, bind_identity
from app.services.practice_accounts import (
    AdminDraft,
    NewPractice,
    PracticeDraft,
    add_practice_for_person,
    add_practice_with_admin,
)
from app.services.rate_limits import SIGNUP_PER_EMAIL, SIGNUP_PER_IP, hit
from app.services.sealing import agreement_signer, seal_agreement
from app.services.team import EMAIL_TAKEN, send_invite

SIGNUP_TOKEN = "signup"
SIGNUP_MINUTES = 30
EMAIL_METHOD = "email"
ACCOUNT_METHOD = "account"
SELF_SOURCE = "self"
TRIAL = "trial"
SIGNED_UP = "practice signed up"
NOT_AVAILABLE = "Self sign-up is not available"
START_AGAIN = "start sign-up again"
NEW_PRACTICE_PATH = "/practices/new"
AGREEMENT_STATEMENT = "I accept the Terms and the Business Associate Agreement, version {version}, for this practice."


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
class AnotherPractice:
    practice_name: str
    time_zone: str
    agreed: bool


def signup_options(settings: Settings, site: Site) -> dict[str, Any]:
    return {
        "enabled": settings.self_signup_enabled and site.takes_signups,
        "terms_url": settings.terms_url,
        "baa_url": settings.baa_url,
        "privacy_url": settings.privacy_url,
        "test_data_only": not settings.baa_url,
    }


def ensure_signup_open() -> None:
    if not get_settings().self_signup_enabled:
        raise NotFound(NOT_AVAILABLE)


def ensure_signup_here(site: Site) -> None:
    if not site.takes_signups:
        raise NotFound(NOT_AVAILABLE)


async def check_email_signup(db: AsyncSession, form: EmailSignup, *, ip: str | None) -> None:
    ensure_signup_open()
    _require_agreement(form.agreed)
    zone_named(form.time_zone)
    await hit(db, SIGNUP_PER_IP, ip)
    await hit(db, SIGNUP_PER_EMAIL, normal_email(form.email))


async def request_email_signup(
    db: AsyncSession, messenger: Messenger, signer: RecordSigner, form: EmailSignup, client: Client
) -> None:
    if await email_in_use(db, form.email, PRACTICE_REALM):
        await _send_existing_account(messenger, normal_email(form.email))
        return
    created = await _trial_practice(
        db, form.practice_name, form.time_zone, AdminDraft(form.name, form.email, "invited")
    )
    created.practice.signup = _signup_record(created, EMAIL_METHOD, client.ip)
    await _seal_agreement(db, signer, created, client)
    await send_invite(db, messenger, created.admin, team_name=created.practice.name)
    _record_signup(db, created, EMAIL_METHOD, client)
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


async def has_account(db: AsyncSession, email: str) -> bool:
    return await account_by_email(db, email, (PRACTICE_REALM,)) is not None


async def complete_identity_signup(
    db: AsyncSession, signer: RecordSigner, token: str | None, form: IdentitySignup, client: Client
) -> Tokens | MfaChallenge:
    identity = pending_identity(token)
    _require_agreement(form.agreed)
    zone_named(form.time_zone)
    await hit(db, SIGNUP_PER_IP, client.ip)
    person = await account_by_email(db, identity.email, (PRACTICE_REALM,))
    if person is None:
        created = await _identity_practice(db, identity, form)
    else:
        await admit(db, person, identity, client)
        created = await _trial_practice_for(db, person, form.practice_name, form.time_zone)
    created.practice.signup = _signup_record(created, identity.provider, client.ip)
    await _seal_agreement(db, signer, created, client)
    _record_signup(db, created, identity.provider, client)
    await db.commit()
    label = provider_label(identity.provider)
    return await sign_in_user(db, created.admin, method=label, client=client, practice_id=created.practice.id)


async def _identity_practice(db: AsyncSession, identity: ProviderIdentity, form: IdentitySignup) -> NewPractice:
    if await email_in_use(db, identity.email, PRACTICE_REALM):
        raise Conflict(EMAIL_TAKEN)
    admin = AdminDraft(form.name, identity.email, "active")
    created = await _trial_practice(db, form.practice_name, form.time_zone, admin)
    await bind_identity(db, created.admin, identity.provider, identity.subject)
    return created


async def start_another_practice(db: AsyncSession, user: User, form: AnotherPractice, client: Client) -> str:
    ensure_signup_open()
    if user.realm != PRACTICE_REALM:
        raise Forbidden("this action needs a practice account")
    _require_agreement(form.agreed)
    zone_named(form.time_zone)
    await hit(db, SIGNUP_PER_IP, client.ip)
    await hit(db, SIGNUP_PER_EMAIL, user.email)
    created = await _trial_practice_for(db, user, form.practice_name, form.time_zone)
    created.practice.signup = _signup_record(created, ACCOUNT_METHOD, client.ip)
    _record_signup(db, created, ACCOUNT_METHOD, client)
    await db.commit()
    return created.practice.id


def _require_agreement(agreed: bool) -> None:
    if agreed is not True:
        raise Invalid("agree to the terms to start a trial")


def _trial_draft(name: str, time_zone: str) -> PracticeDraft:
    settings = get_settings()
    zone = zone_named(time_zone)
    ends = today_in(zone) + timedelta(days=settings.trial_days)
    return PracticeDraft(name, TRIAL, TRIAL, settings.trial_seats, zone.key, renews_on=ends)


async def _trial_practice(db: AsyncSession, name: str, time_zone: str, admin: AdminDraft) -> NewPractice:
    return await add_practice_with_admin(db, _trial_draft(name, time_zone), admin)


async def _trial_practice_for(db: AsyncSession, person: User, name: str, time_zone: str) -> NewPractice:
    return await add_practice_for_person(db, _trial_draft(name, time_zone), person)


def _signup_record(created: NewPractice, method: str, ip: str | None) -> dict[str, Any]:
    return {
        "source": SELF_SOURCE,
        "agreement_version": get_settings().agreement_version,
        "accepted_at": utcnow().isoformat(),
        "accepted_by": created.admin.id,
        "method": method,
        "ip": ip,
    }


async def _seal_agreement(db: AsyncSession, signer: RecordSigner, created: NewPractice, client: Client) -> None:
    signed_by = agreement_signer(created.admin, created.membership.role, client)
    statement = AGREEMENT_STATEMENT.format(version=get_settings().agreement_version)
    await seal_agreement(db, signer, signed_by, created.practice, statement=statement)


def _record_signup(db: AsyncSession, created: NewPractice, method: str, client: Client) -> None:
    actor = Actor(created.admin, created.practice, client.ip, client.agent, membership=created.membership)
    detail = f"{created.practice.name}, {method}"
    record_activity(db, actor, SIGNED_UP, practice_id=created.practice.id, detail=detail)


async def _send_existing_account(messenger: Messenger, email: str) -> None:
    app_url = get_settings().app_url
    await messenger.email(
        email,
        subject="You already have a Bodha Assure account",
        body=(
            "Someone asked to start a Bodha Assure trial with this email, which already has an account. "
            f"To add a practice to it, sign in: {app_url}/sign-in?next={NEW_PRACTICE_PATH}. "
            f"Forgot your password? Reset it: {app_url}/forgot-password. "
            "If this was not you, you can ignore this email."
        ),
    )
