import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
import pyotp

from app.core.config import get_settings

ALGORITHM = "HS256"
PASSWORD_MIN_LENGTH = 10


class TokenError(Exception):
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


def verify_mfa(secret: str | None, code: str) -> bool:
    return secret is not None and pyotp.TOTP(secret).verify(code, valid_window=1)
