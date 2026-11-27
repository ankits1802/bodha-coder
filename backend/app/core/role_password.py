from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

RUNTIME_ROLE = "bodha_runtime"
SCRAM_ITERATIONS = 4096
SALT_BYTES = 16


def scram_verifier(password: str) -> str:
    if not password.isalnum():
        raise ValueError("the runtime database password must be letters and digits only")
    salt = secrets.token_bytes(SALT_BYTES)
    salted = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, SCRAM_ITERATIONS)
    stored = hashlib.sha256(hmac.new(salted, b"Client Key", hashlib.sha256).digest()).digest()
    server = hmac.new(salted, b"Server Key", hashlib.sha256).digest()
    salt_text, stored_text, server_text = (base64.b64encode(part).decode("ascii") for part in (salt, stored, server))
    return f"SCRAM-SHA-256${SCRAM_ITERATIONS}:{salt_text}${stored_text}:{server_text}"
