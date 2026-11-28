from __future__ import annotations

import re
import secrets
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.core.deps import practice_access
from app.core.roles import HQ_ROLE
from app.core.security import hash_password
from app.models import PRACTICE_REALM, User
from app.services.auth import access_token_for
from app.services.two_step import enrol_secret
from tests.e2e_seed.api import Api, Caller, SeedFailed, admin_host, practice_host

__all__ = ["Account", "accept_invite", "create_hq_account", "enrol_two_step", "practice_caller", "hq_caller"]

PASSWORD_BYTES = 12
INVITE_LINK = re.compile(r"/set-password#(?P<token>[\w.~-]+)")


@dataclass(frozen=True)
class Account:
    id: str
    name: str
    email: str
    password: str
    role: str
    two_step_secret: str | None = None

    def view(self) -> dict[str, Any]:
        return asdict(self)


def new_password() -> str:
    return "Synthetic-" + secrets.token_urlsafe(PASSWORD_BYTES)


async def create_hq_account(name: str, email: str, *, two_step: bool) -> Account:
    password = new_password()
    async with SessionFactory() as db:
        user = User(email=email, name=name, role=HQ_ROLE, status="active", password_hash=hash_password(password))
        secret = enrol_secret(user) if two_step else None
        user.mfa_enabled = two_step
        db.add(user)
        await db.commit()
    return Account(user.id, name, email, password, HQ_ROLE, secret)


async def enrol_two_step(account: Account) -> Account:
    async with SessionFactory() as db:
        user = await db.get_one(User, account.id)
        secret = enrol_secret(user)
        user.mfa_enabled = True
        await db.commit()
    return replace(account, two_step_secret=secret)


async def hq_caller(account: Account) -> Caller:
    return Caller(await _token(account.id, None), admin_host())


async def practice_caller(account: Account, practice_id: str) -> Caller:
    return Caller(await _token(account.id, practice_id), practice_host())


async def accept_invite(api: Api, *, name: str, email: str, role: str) -> Account:
    password = new_password()
    token = _invite_token(email)
    await api.send(
        Caller(None, practice_host()), "POST", "/api/auth/password", json={"token": token, "password": password}
    )
    async with SessionFactory() as db:
        user_id = await db.scalar(select(User.id).where(User.email == email, User.realm == PRACTICE_REALM))
    if user_id is None:
        raise SeedFailed(f"no practice account holds {email}")
    return Account(user_id, name, email, password, role)


async def _token(user_id: str, practice_id: str | None) -> str:
    async with SessionFactory() as db:
        user = await db.get_one(User, user_id)
        return access_token_for(user, await practice_access(db, user, practice_id))


def _invite_token(email: str) -> str:
    folder = get_settings().mail_outbox_dir
    if not folder:
        raise SeedFailed("set MAIL_OUTBOX_DIR so invitations can be read")
    for path in sorted(Path(folder).glob("*.txt"), reverse=True):
        text = path.read_text(encoding="utf-8")
        found = INVITE_LINK.search(text) if text.startswith(f"To: {email}\n") else None
        if found:
            return found["token"]
    raise SeedFailed(f"no set-password email reached {email}")
