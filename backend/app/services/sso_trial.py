from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.saml_response import SamlIdentity
from app.core.deps import Actor, Client
from app.core.errors import NotFound, Unauthorized
from app.core.security import TokenError, issue_token, read_token
from app.models import PRACTICE_REALM, SsoConnection, SsoVersion, User
from app.services.account_lookup import account_by_email
from app.services.auth_events import AuthEventFacts, record_auth_event
from app.services.domain_claims import ClaimScope
from app.services.email_domains import domain_of
from app.services.sso_policy import current_version, owner_practice_ids
from app.services.sso_settings import NOT_SET_UP, live_connection

__all__ = [
    "SSO_TESTED",
    "TrialOutcome",
    "TrialSummary",
    "record_trial",
    "start_trial_path",
    "trial_result",
    "failed_trial",
    "scoped_trial_result",
    "tester_of",
    "trial_link",
    "trial_summary",
]

SSO_TESTED = "sso_tested"
TEST_TOKEN = "saml_test"
RESULT_TOKEN = "saml_result"
TEST_MINUTES = 5
RESULT_MINUTES = 5
START_PATH = "/api/auth/saml/{connection_id}/start"
PRACTICE_PAGE = "/settings/security"
ORGANIZATION_PAGE = "/organizations/{organization_id}/sign-in"
RESULT_FRAGMENT = "sso_test"
EXPIRED = "this test has expired; start it again"
NOT_SAVED = "save the single sign-on settings before testing them"


@dataclass(frozen=True)
class TrialSummary:
    reason: str | None
    domain: str | None
    in_domains: bool
    account: bool
    mfa: bool
    context_class: str | None
    name_found: bool


@dataclass(frozen=True)
class TrialOutcome:
    page: str


async def trial_link(db: AsyncSession, actor: Actor, scope: ClaimScope) -> dict[str, str]:
    connection = await live_connection(db, scope)
    if connection is None or await current_version(db, connection.id) is None:
        raise NotFound(NOT_SAVED)
    return {"url": start_trial_path(actor, connection.id)}


async def scoped_trial_result(db: AsyncSession, actor: Actor, scope: ClaimScope, token: str) -> dict[str, Any]:
    connection = await live_connection(db, scope)
    if connection is None:
        raise NotFound(NOT_SET_UP)
    return trial_result(actor, connection.id, token)


def start_trial_path(actor: Actor, connection_id: str) -> str:
    token = issue_token(TEST_TOKEN, actor.user.id, TEST_MINUTES, cfg=connection_id)
    return f"{START_PATH.format(connection_id=connection_id)}?{urlencode({'test': token})}"


def tester_of(token: str, connection_id: str) -> str:
    try:
        claims = read_token(token, TEST_TOKEN)
    except TokenError as error:
        raise Unauthorized(EXPIRED) from error
    if claims.get("cfg") != connection_id:
        raise Unauthorized(EXPIRED)
    return str(claims["sub"])


async def trial_summary(
    db: AsyncSession, version: SsoVersion, identity: SamlIdentity, *, in_domains: bool
) -> TrialSummary:
    account = await account_by_email(db, identity.email, (PRACTICE_REALM,))
    mfa = bool(version.mfa_context) and identity.context_class == version.mfa_context
    return TrialSummary(
        reason=None,
        domain=domain_of(identity.email),
        in_domains=in_domains,
        account=account is not None,
        mfa=mfa,
        context_class=identity.context_class,
        name_found=bool(identity.name),
    )


def failed_trial(reason: str) -> TrialSummary:
    return TrialSummary(reason, None, False, False, False, None, False)


async def record_trial(
    db: AsyncSession, connection: SsoConnection, tester_id: str, summary: TrialSummary, *, client: Client
) -> TrialOutcome:
    tester = await db.get(User, tester_id)
    detail = "passed" if summary.reason is None else f"failed: {summary.reason}"
    practice_ids = await owner_practice_ids(
        db, practice_id=connection.practice_id, organization_id=connection.organization_id
    )
    for practice_id in practice_ids or [None]:
        await record_auth_event(db, SSO_TESTED, tester, AuthEventFacts(client, practice_id=practice_id, detail=detail))
    await db.commit()
    token = issue_token(RESULT_TOKEN, tester_id, RESULT_MINUTES, cfg=connection.id, **_claims(summary))
    return TrialOutcome(f"{_page(connection)}#{urlencode({RESULT_FRAGMENT: token})}")


def trial_result(actor: Actor, connection_id: str, token: str) -> dict[str, Any]:
    try:
        claims = read_token(token, RESULT_TOKEN)
    except TokenError as error:
        raise Unauthorized(EXPIRED) from error
    if claims.get("sub") != actor.user.id or claims.get("cfg") != connection_id:
        raise Unauthorized(EXPIRED)
    return {
        "passed": claims.get("reason") is None,
        "reason": claims.get("reason"),
        "domain": claims.get("domain"),
        "in_domains": bool(claims.get("in_domains")),
        "account": bool(claims.get("account")),
        "mfa": bool(claims.get("mfa")),
        "context_class": claims.get("context_class"),
        "name_found": bool(claims.get("name_found")),
    }


def _claims(summary: TrialSummary) -> dict[str, Any]:
    return {
        "reason": summary.reason,
        "domain": summary.domain,
        "in_domains": summary.in_domains,
        "account": summary.account,
        "mfa": summary.mfa,
        "context_class": summary.context_class,
        "name_found": summary.name_found,
    }


def _page(connection: SsoConnection) -> str:
    if connection.organization_id is not None:
        return ORGANIZATION_PAGE.format(organization_id=connection.organization_id)
    return PRACTICE_PAGE
