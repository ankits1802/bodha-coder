from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.adapters.oidc import ProviderIdentity
from app.adapters.oidc_providers import provider_label
from app.adapters.seal_keys import RecordSigner
from app.core.deps import Client
from app.core.errors import Conflict
from app.models import PRACTICE_REALM, User
from app.services.account_lookup import account_by_email, email_in_use, normal_email
from app.services.auth import MfaChallenge, Tokens, sign_in_user
from app.services.domain_join import (
    AUTO,
    JOINED,
    REQUESTED,
    JoinOffer,
    admit_by_domain,
    join_offer_for,
    offer_view,
    read_join_ticket,
    request_by_domain,
    room_for,
)
from app.services.identity_sign_in import admit, bind_identity
from app.services.rate_limits import SIGNUP_PER_IP, hit
from app.services.signup import EmailSignup, ensure_signup_open, pending_identity, start_email_trial
from app.services.sso_policy import ensure_service_allowed
from app.services.team import EMAIL_TAKEN, send_invite

__all__ = ["STARTED", "complete_email_join", "complete_identity_join", "join_page"]

STARTED = "started"
HAS_ACCOUNT = "this email already has an account; sign in instead"
NO_LONGER_OPEN = "that practice is no longer taking people from this domain"
INVITED, ACTIVE = "invited", "active"


async def join_page(db: AsyncSession, token: str) -> dict[str, Any]:
    ensure_signup_open()
    ticket = read_join_ticket(token)
    return {
        "email": ticket.email,
        "name": ticket.name,
        "own_practice_name": ticket.practice_name,
        "join": offer_view(await join_offer_for(db, ticket.email)),
    }


async def complete_email_join(
    db: AsyncSession, messenger: Messenger, signer: RecordSigner, token: str, *, join: bool, client: Client
) -> str:
    ensure_signup_open()
    ticket = read_join_ticket(token)
    await hit(db, SIGNUP_PER_IP, client.ip)
    if await email_in_use(db, ticket.email, PRACTICE_REALM):
        raise Conflict(HAS_ACCOUNT)
    await ensure_service_allowed(db, ticket.email)
    if not join:
        form = EmailSignup(ticket.name, ticket.practice_name, ticket.email, ticket.time_zone, True)
        await start_email_trial(db, messenger, signer, form, client)
        return STARTED
    offer = await _open_offer(db, ticket.email)
    if offer.mode == AUTO and await room_for(db, offer.practice_id):
        person = User(email=normal_email(ticket.email), name=ticket.name.strip(), role=offer.role, status=INVITED)
        db.add(person)
        await db.flush()
        await admit_by_domain(db, offer, person)
        await send_invite(db, messenger, person, team_name=offer.practice_name)
        await db.commit()
        return JOINED
    await request_by_domain(db, offer, name=ticket.name, email=ticket.email)
    await db.commit()
    return REQUESTED


async def _open_offer(db: AsyncSession, email: str) -> JoinOffer:
    offer = await join_offer_for(db, email)
    if offer is None:
        raise Conflict(NO_LONGER_OPEN)
    return offer


async def complete_identity_join(
    db: AsyncSession, token: str | None, *, name: str, client: Client
) -> Tokens | MfaChallenge | None:
    identity = pending_identity(token)
    await hit(db, SIGNUP_PER_IP, client.ip)
    await ensure_service_allowed(db, identity.email)
    offer = await _open_offer(db, identity.email)
    if offer.mode == AUTO and await room_for(db, offer.practice_id):
        person = await _person_for(db, identity, name=name, role=offer.role, client=client)
        await admit_by_domain(db, offer, person)
        await db.commit()
        label = provider_label(identity.provider)
        return await sign_in_user(db, person, method=label, client=client, practice_id=offer.practice_id)
    await request_by_domain(db, offer, name=name or identity.name or identity.email, email=identity.email)
    await db.commit()
    return None


async def _person_for(db: AsyncSession, identity: ProviderIdentity, *, name: str, role: str, client: Client) -> User:
    person = await account_by_email(db, identity.email, (PRACTICE_REALM,))
    if person is not None:
        await admit(db, person, identity, client)
        return person
    if await email_in_use(db, identity.email, PRACTICE_REALM):
        raise Conflict(EMAIL_TAKEN)
    created = User(email=normal_email(identity.email), name=name.strip(), role=role, status=ACTIVE)
    db.add(created)
    await db.flush()
    await bind_identity(db, created, identity.provider, identity.subject)
    return created
