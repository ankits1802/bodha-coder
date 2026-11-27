import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
import pyotp
from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.core.config import get_settings
from app.core.errors import Unavailable

ALGORITHM = "HS256"
PASSWORD_MIN_LENGTH = 10
MFA_DRIFT_STEPS = 1
MFA_SECRET_PREFIX = "v1:"


class TokenError(Exception):
    pass


class MfaKeyUnavailable(Unavailable):
    pass


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        bcrypt.checkpw(b"timing-equaliser", bcrypt.hashpw(b"x", bcrypt.gensalt(4)))
        return False
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def random_token() -> str:
    return secrets.token_urlsafe(32)


def random_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def same_digest(value: str, expected_digest: str | None) -> bool:
    return expected_digest is not None and hmac.compare_digest(digest(value), expected_digest)


def issue_token(typ: str, subject: str, minutes: int, **claims: Any) -> str:
    now = datetime.now(UTC)
    payload = {"typ": typ, "sub": subject, "iat": now, "exp": now + timedelta(minutes=minutes), **claims}
    return jwt.encode(payload, get_settings().secret_key, algorithm=ALGORITHM)


def read_token(token: str, typ: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError as error:
        raise TokenError("invalid token") from error
    if payload.get("typ") != typ:
        raise TokenError("wrong token type")
    return payload


def new_mfa_secret() -> str:
    return pyotp.random_base32()


def mfa_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=get_settings().mfa_issuer)


def mfa_step_for(secret: str, code: str, *, after: int | None) -> int | None:
    totp = pyotp.TOTP(secret)
    current = totp.timecode(datetime.now(UTC))
    for step in range(current - MFA_DRIFT_STEPS, current + MFA_DRIFT_STEPS + 1):
        if (after is None or step > after) and hmac.compare_digest(totp.generate_otp(step), code):
            return step
    return None


def is_sealed_mfa_secret(stored: str) -> bool:
    return stored.startswith(MFA_SECRET_PREFIX)


def seal_mfa_secret(secret: str) -> str:
    return MFA_SECRET_PREFIX + _mfa_cipher().encrypt(secret.encode()).decode()


def open_mfa_secret(stored: str) -> str:
    if not is_sealed_mfa_secret(stored):
        return stored
    try:
        return _mfa_cipher().decrypt(stored.removeprefix(MFA_SECRET_PREFIX).encode()).decode()
    except InvalidToken as error:
        raise MfaKeyUnavailable("two-step verification cannot be read on this server") from error


def mfa_secret_is_current(stored: str) -> bool:
    if not is_sealed_mfa_secret(stored):
        return False
    try:
        _mfa_keys()[0].decrypt(stored.removeprefix(MFA_SECRET_PREFIX).encode())
    except InvalidToken:
        return False
    return True


def _mfa_cipher() -> MultiFernet:
    return MultiFernet(_mfa_keys())


def _mfa_keys() -> list[Fernet]:
    keys = [key.strip() for key in (get_settings().mfa_encryption_key or "").split(",") if key.strip()]
    if not keys:
        raise MfaKeyUnavailable("two-step verification is not set up on this server")
    try:
        return [Fernet(key) for key in keys]
    except ValueError as error:
        raise MfaKeyUnavailable("two-step verification is not set up on this server") from error
