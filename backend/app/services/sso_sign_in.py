from __future__ import annotations

import asyncio
import hmac
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.saml_request import authn_request, new_request_id, redirect_url
from app.adapters.saml_response import ResponseRules, SamlIdentity, SamlRefused, read_response
from app.core.deps import ACTIVE_PRACTICE_STATUSES, Client, PlanEnded, plan_ended_on
from app.core.errors import Conflict, Forbidden, NotFound, Unauthorized
from app.core.realms import Site
from app.core.security import TokenError, digest, issue_token, random_token, read_token
from app.models import PRACTICE_REALM, DomainClaim, Practice, SsoAssertion, SsoConnection, SsoVersion, User, utcnow
from app.services.account_lookup import account_by_email, email_in_use, normal_email
from app.services.audit_log import SystemActor, record_system_access
from app.services.auth import MfaChallenge, Tokens, sign_in_user, start_session
from app.services.auth_events import SIGN_IN_FAILED, AuthEventFacts, record_auth_event
from app.services.memberships import ACTIVE, BLOCKED, INVITED, accept_invitations, enrol, landing_access
from app.services.plan_limits import ensure_user_room
from app.services.rate_limits import SSO_LOOKUPS_PER_IP, SSO_PER_IP, hit
from app.services.sso_policy import current_version, owner_practice_ids, route_for_email, service_provider
from app.services.sso_trial import TrialOutcome, failed_trial, record_trial, tester_of, trial_summary

__all__ = [
    "START_MINUTES",
    "SamlPost",
    "SamlStart",
    "SsoBounce",
    "SsoOutcome",
    "SsoRefusal",
    "SsoSignedIn",
    "discover",
    "finish",
    "same_site_path",
    "start",
]

START_TOKEN = "saml_start"
START_MINUTES = 10
RELAY_LENGTH = 16
NEXT_LENGTH = 512
SAME_SITE_PATH = re.compile(r"^/(?![/\\])[A-Za-z0-9\-._~!$&'()*+,;=:@%/?]*$")
START_PATH = "/api/auth/saml/{connection_id}/start"
SSO_METHOD = "single sign-on"
SSO_TWO_STEP_METHOD = "single sign-on with the identity provider's two-step"
SSO_SYSTEM = SystemActor("bodha-sso", "Single sign-on")
REFUSED_ACTION = "single sign-on refused"
JOINED_ACTION = "joined by single sign-on"
FAILED = "sso_failed"
PUBLIC_REASONS = {
    "request": "sso_expired",
    "relay": "sso_expired",
    "domain": "sso_domain",
    "no_account": "no_account",
    "blocked": "blocked",
    "plan_ended": "plan_ended",
    "no_seat": "no_seat",
    "no_practice": "no_practice",
}
NOT_SET_UP = "single sign-on is not set up here"
NAME_LENGTH = 120


class SsoStopped(Exception):
    def __init__(self, reason: str, *, user: User | None = None, email: str | None = None) -> None:
        super().__init__(reason)
        self.reason, self.user, self.email = reason, user, email


@dataclass(frozen=True)
class SamlStart:
    url: str
    cookie: str


@dataclass(frozen=True)
class SamlPost:
    response: str
    relay_state: str | None
    cookie: str | None


@dataclass(frozen=True)
class Started:
    request_id: str
    relay: str
    next_path: str | None
    tester_id: str | None


@dataclass(frozen=True)
class SsoSignedIn:
    result: Tokens | MfaChallenge
    next_path: str | None


@dataclass(frozen=True)
class SsoBounce:
    path: str


@dataclass(frozen=True)
class SsoRefusal:
    reason: str


SsoOutcome = SsoSignedIn | SsoBounce | SsoRefusal | TrialOutcome


def same_site_path(value: object) -> str | None:
    if not isinstance(value, str) or not value or len(value) > NEXT_LENGTH:
        return None
    if not SAME_SITE_PATH.fullmatch(value) or value.startswith("/api/"):
        return None
    return value


def start_path(connection_id: str, next_path: str | None) -> str:
    base = START_PATH.format(connection_id=connection_id)
    return f"{base}?{urlencode({'next': next_path})}" if next_path else base


async def discover(db: AsyncSession, email: str, site: Site, *, client: Client) -> dict[str, Any]:
    await hit(db, SSO_LOOKUPS_PER_IP, client.ip)
    route = await route_for_email(db, email) if PRACTICE_REALM in site.realms else None
    if route is None:
        return {"mode": "none", "start_url": None}
    return {"mode": "required" if route.required else "optional", "start_url": start_path(route.connection.id, None)}


async def start(db: AsyncSession, connection_id: str, *, next_path: str | None, test: str | None) -> SamlStart:
    found = await _live(db, connection_id)
    if found is None:
        raise NotFound(NOT_SET_UP)
    connection, version = found
    tester = tester_of(test, connection.id) if test else None
    request_id, relay = new_request_id(), random_token()[:RELAY_LENGTH]
    claims = {"cfg": connection.id, "rs": relay, "next": same_site_path(next_path), "test": tester}
    cookie = issue_token(START_TOKEN, request_id, START_MINUTES, **claims)
    xml = authn_request(
        service_provider(connection.id), request_id=request_id, destination=version.sso_url, issued_at=utcnow()
    )
    return SamlStart(redirect_url(version.sso_url, xml, relay_state=relay), cookie)


async def finish(db: AsyncSession, connection_id: str, posted: SamlPost, *, client: Client) -> SsoOutcome:
    await hit(db, SSO_PER_IP, client.ip)
    found = await _live(db, connection_id)
    if found is None:
        return SsoRefusal(FAILED)
    connection, version = found
    started = _started(posted.cookie, connection.id)
    try:
        identity = await _verified_identity(db, connection, version, posted, started)
        if started is None:
            return SsoBounce(start_path(connection.id, same_site_path(posted.relay_state)))
        if started.tester_id is not None:
            in_domains = await _claim_for(db, connection, identity.email) is not None
            summary = await trial_summary(db, version, identity, in_domains=in_domains)
            return await record_trial(db, connection, started.tester_id, summary, client=client)
        return await _sign_in(db, connection, version, identity, started=started, client=client)
    except SsoStopped as stop:
        return await _refused(db, connection, started, stop, client)


async def _live(db: AsyncSession, connection_id: str) -> tuple[SsoConnection, SsoVersion] | None:
    connection = await db.get(SsoConnection, connection_id)
    if connection is None or connection.removed_at is not None:
        return None
    version = await current_version(db, connection.id)
    return None if version is None else (connection, version)


def _started(cookie: str | None, connection_id: str) -> Started | None:
    if not cookie:
        return None
    try:
        claims = read_token(cookie, START_TOKEN)
    except TokenError:
        return None
    relay, tester = claims.get("rs"), claims.get("test")
    if claims.get("cfg") != connection_id or not isinstance(relay, str):
        return None
    return Started(str(claims["sub"]), relay, same_site_path(claims.get("next")), str(tester) if tester else None)


async def _verified_identity(
    db: AsyncSession, connection: SsoConnection, version: SsoVersion, posted: SamlPost, started: Started | None
) -> SamlIdentity:
    rules = ResponseRules(
        sp=service_provider(connection.id),
        idp_entity_id=version.idp_entity_id,
        certificates=tuple(version.certificates),
        request_id=started.request_id if started is not None else None,
        email_attribute=version.email_attribute,
        name_attribute=version.name_attribute,
        now=utcnow(),
    )
    try:
        identity = await asyncio.to_thread(read_response, posted.response, rules)
    except SamlRefused as refusal:
        raise SsoStopped(refusal.reason) from refusal
    if started is not None and not hmac.compare_digest((posted.relay_state or "").encode(), started.relay.encode()):
        raise SsoStopped("relay", email=identity.email)
    await _consume(db, connection.id, identity)
    return identity


async def _consume(db: AsyncSession, connection_id: str, identity: SamlIdentity) -> None:
    key = digest(f"{identity.issuer}\n{identity.assertion_id}")
    try:
        async with db.begin_nested():
            db.add(SsoAssertion(connection_id=connection_id, assertion_key=key, expires_at=identity.keep_until))
    except IntegrityError as error:
        raise SsoStopped("replayed", email=identity.email) from error
    await db.commit()


async def _claim_for(db: AsyncSession, connection: SsoConnection, email: str) -> DomainClaim | None:
    route = await route_for_email(db, email)
    if route is None or route.connection.id != connection.id:
        return None
    return route.claim


async def _sign_in(
    db: AsyncSession,
    connection: SsoConnection,
    version: SsoVersion,
    identity: SamlIdentity,
    *,
    started: Started,
    client: Client,
) -> SsoSignedIn:
    claim = await _claim_for(db, connection, identity.email)
    if claim is None:
        raise SsoStopped("domain", email=identity.email)
    user = await account_by_email(db, identity.email, (PRACTICE_REALM,))
    if user is None:
        user = await _new_person(db, version, claim, identity)
    await _admit(db, user, identity, client)
    await db.commit()
    return SsoSignedIn(await _session(db, user, version, identity, client), started.next_path)


async def _new_person(db: AsyncSession, version: SsoVersion, claim: DomainClaim, identity: SamlIdentity) -> User:
    role = version.new_person_role
    if not version.create_people or role is None or await email_in_use(db, identity.email, PRACTICE_REALM):
        raise SsoStopped("no_account", email=identity.email)
    practice = await db.get(Practice, claim.practice_id, with_for_update=True)
    if practice is None or practice.status not in ACTIVE_PRACTICE_STATUSES:
        raise SsoStopped("no_practice", email=identity.email)
    if plan_ended_on(practice) is not None:
        raise SsoStopped("plan_ended", email=identity.email)
    try:
        await ensure_user_room(db, practice)
    except Conflict as error:
        raise SsoStopped("no_seat", email=identity.email) from error
    name = (identity.name or identity.email.split("@", 1)[0])[:NAME_LENGTH]
    person = User(email=normal_email(identity.email), name=name, role=role, status=ACTIVE)
    db.add(person)
    await db.flush()
    await enrol(db, person, practice.id, role, invited_by=None)
    record_system_access(db, SSO_SYSTEM, practice.id, JOINED_ACTION, detail=f"{person.name} as {role}")
    return person


async def _admit(db: AsyncSession, user: User, identity: SamlIdentity, client: Client) -> None:
    if user.status == BLOCKED:
        raise SsoStopped("blocked", user=user, email=identity.email)
    if user.status == INVITED:
        await accept_invitations(db, user, client)
        user.status = ACTIVE


async def _session(
    db: AsyncSession, user: User, version: SsoVersion, identity: SamlIdentity, client: Client
) -> Tokens | MfaChallenge:
    try:
        if version.mfa_context and identity.context_class == version.mfa_context:
            standing = await landing_access(db, user)
            method = SSO_TWO_STEP_METHOD
            return await start_session(db, user, standing, method=method, client=client, idp_two_step=True)
        return await sign_in_user(db, user, method=SSO_METHOD, client=client)
    except PlanEnded as error:
        raise SsoStopped("plan_ended", user=user, email=identity.email) from error
    except (Unauthorized, Forbidden) as error:
        raise SsoStopped("no_practice", user=user, email=identity.email) from error


async def _refused(
    db: AsyncSession, connection: SsoConnection, started: Started | None, stop: SsoStopped, client: Client
) -> SsoRefusal | TrialOutcome:
    if started is not None and started.tester_id is not None:
        return await record_trial(db, connection, started.tester_id, failed_trial(stop.reason), client=client)
    facts = AuthEventFacts(client, detail=f"single sign-on: {stop.reason}", email=stop.email, realm=PRACTICE_REALM)
    await record_auth_event(db, SIGN_IN_FAILED, stop.user, facts)
    if stop.user is None:
        owners = await owner_practice_ids(
            db, practice_id=connection.practice_id, organization_id=connection.organization_id
        )
        for practice_id in owners:
            record_system_access(db, SSO_SYSTEM, practice_id, REFUSED_ACTION, detail=stop.reason)
    await db.commit()
    return SsoRefusal(PUBLIC_REASONS.get(stop.reason, FAILED))
