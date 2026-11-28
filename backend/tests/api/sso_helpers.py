from __future__ import annotations

import base64
import zlib
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

from lxml import etree
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import Session, User
from tests.api.organization_helpers import verified_domain
from tests.builders import Harness
from tests.builders import Practice as BuiltPractice
from tests.saml_idp import IDP_ENTITY, IDP_SSO_URL, Assertion, IdpKeys, encoded, signed_response

PRACTICE_SSO = "/api/practice/sso"
SAML_COOKIE = "bodha_saml"
ANNA = "anna@lakeside.example.com"


@dataclass(frozen=True)
class SsoSetup:
    connection_id: str
    claim_id: str


@dataclass(frozen=True)
class Started:
    request_id: str
    relay: str
    cookie: str | None


def saml_base(connection_id: str) -> str:
    return f"{get_settings().app_url.rstrip('/')}/api/auth/saml/{connection_id}"


def assertion_for(connection_id: str, **changes: Any) -> Assertion:
    base = saml_base(connection_id)
    return Assertion(acs_url=f"{base}/acs", audience=f"{base}/metadata", **changes)


def settings_body(keys: tuple[IdpKeys, ...], *, claim_ids: list[str], **changes: Any) -> dict[str, Any]:
    provider = {
        "entity_id": IDP_ENTITY,
        "sso_url": IDP_SSO_URL,
        "certificates": [pair.compact for pair in keys],
        "metadata_url": None,
    }
    return {
        "identity_provider": provider,
        "claim_ids": claim_ids,
        "email_attribute": None,
        "name_attribute": "displayName",
        "create_people": False,
        "new_person_role": "viewer",
        "required": False,
        "break_glass": [],
        "mfa_context": None,
        **changes,
    }


async def connection_for(harness: Harness, admin: dict[str, str], path: str = PRACTICE_SSO) -> str:
    created = await harness.client.post(path, headers=admin)
    assert created.status_code == 200, created.text
    return created.json()["connection"]["id"]


async def save_settings(harness: Harness, admin: dict[str, str], body: dict[str, Any], path: str = PRACTICE_SSO):
    return await harness.client.put(path, headers=admin, json=body)


async def sso_ready(harness: Harness, practice: BuiltPractice, keys: IdpKeys, **changes: Any) -> SsoSetup:
    claim_id = await verified_domain(harness, practice.admin, mode="off")
    connection_id = await connection_for(harness, practice.admin)
    saved = await save_settings(harness, practice.admin, settings_body((keys,), claim_ids=[claim_id], **changes))
    assert saved.status_code == 200, saved.text
    return SsoSetup(connection_id, claim_id)


async def start(
    harness: Harness, connection_id: str, *, url: str | None = None, next_path: str | None = None
) -> Started:
    target = url or f"/api/auth/saml/{connection_id}/start"
    response = await harness.client.get(target, params={"next": next_path} if next_path else None)
    assert response.status_code == 302, response.text
    query = parse_qs(urlsplit(response.headers["location"]).query)
    request = etree.fromstring(zlib.decompress(base64.b64decode(query["SAMLRequest"][0]), -15))
    cookie = harness.client.cookies.get(SAML_COOKIE, domain="app.test", path=f"/api/auth/saml/{connection_id}")
    return Started(str(request.get("ID")), query["RelayState"][0], cookie)


async def post_back(harness: Harness, connection_id: str, saml_response: str, relay: str | None):
    form = {"SAMLResponse": saml_response} if relay is None else {"SAMLResponse": saml_response, "RelayState": relay}
    return await harness.client.post(f"/api/auth/saml/{connection_id}/acs", data=form)


async def sso_round_trip(harness: Harness, connection_id: str, keys: IdpKeys, **changes: Any):
    started = await start(harness, connection_id)
    facts = assertion_for(connection_id, in_response_to=started.request_id, **changes)
    return await post_back(harness, connection_id, encoded(signed_response(facts, keys)), started.relay)


def sign_in_location(fragment: str, *, next_path: str | None = None) -> str:
    query = f"?{urlencode({'next': next_path})}" if next_path else ""
    return f"{get_settings().app_url}/sign-in{query}#{fragment}"


def refused_location(reason: str) -> str:
    return sign_in_location(urlencode({"error": reason, "provider": "sso"}))


async def refreshed_email(harness: Harness) -> str:
    refreshed = await harness.client.post("/api/auth/refresh")
    assert refreshed.status_code == 200, refreshed.text
    return refreshed.json()["user"]["email"]


async def person(email: str) -> User | None:
    async with SessionFactory() as db:
        return await db.scalar(select(User).where(User.email == email))


async def sessions_of(user_id: str) -> list[Session]:
    async with SessionFactory() as db:
        rows = await db.scalars(select(Session).where(Session.user_id == user_id).order_by(Session.created_at))
        return list(rows.all())
