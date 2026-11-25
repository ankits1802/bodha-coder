from __future__ import annotations

from app.core.security import is_sealed_mfa_secret, mfa_step_for, new_mfa_secret, open_mfa_secret, seal_mfa_secret
from app.models import User


def enrol_secret(user: User) -> str:
    secret = new_mfa_secret()
    user.mfa_secret, user.mfa_last_step = seal_mfa_secret(secret), None
    return secret


def accept_code(user: User, code: str) -> bool:
    if user.mfa_secret is None:
        return False
    secret = open_mfa_secret(user.mfa_secret)
    step = mfa_step_for(secret, code.strip(), after=user.mfa_last_step)
    if step is None:
        return False
    user.mfa_last_step = step
    if not is_sealed_mfa_secret(user.mfa_secret):
        user.mfa_secret = seal_mfa_secret(secret)
    return True


def forget_two_step(user: User) -> None:
    user.mfa_enabled, user.mfa_secret, user.mfa_last_step = False, None, None
